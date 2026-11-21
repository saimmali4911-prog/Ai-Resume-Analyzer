import os
import uuid
import re
from datetime import datetime, timezone
from flask import Flask, request, jsonify, send_file, abort
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from email_validator import validate_email, EmailNotValidError

from config import Config
from models import (
    db, User, Profile, Resume,
    ResumeAnalysis, ATSAnalysis, JobMatch, Improvement
)
from services.extract import extract_text
from services.rules import ats_rules
from services import nlp

app = Flask(__name__)
app.config.from_object(Config)
@app.route("/", methods=["GET"])
def home():
    return {
        "status": "success",
        "message": "ResumeXpert AI API is running!"
    }, 200
# Enable CORS for all routes under /api, supporting credentials and all origins
CORS(
    app,
    resources={r"/api/*": {"origins": "*"}},
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
)

db.init_app(app)

serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

login_manager = LoginManager(app)

@login_manager.user_loader
def load_user(uid):
    try:
        return db.session.get(User, int(uid))
    except (ValueError, TypeError):
        return None

@login_manager.request_loader
def load_user_from_request(req):
    auth_header = req.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ', 1)[1].strip()
        try:
            user_id = serializer.loads(token, salt='resume-auth-token', max_age=86400 * 30)
            return db.session.get(User, int(user_id))
        except (BadSignature, SignatureExpired, ValueError, TypeError):
            return None
    return None

@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({'error': 'Authentication required. Please log in.'}), 401

def generate_token(user_id):
    return serializer.dumps(user_id, salt='resume-auth-token')

KINDS = {
    'analysis': (ResumeAnalysis, 'Resume Analysis', 'Get a score with strengths, weaknesses and detailed feedback.'),
    'ats': (ATSAnalysis, 'ATS Compatibility Checker', 'Rule-based formatting checks plus TF-IDF keyword evaluation.'),
    'match': (JobMatch, 'Job Description Matching', 'Paste a job description and see how well your resume fits.'),
    'improve': (Improvement, 'Resume Improvement Suggestions', 'Get keyword and structure suggestions to improve your resume.'),
}

SECTIONS = [
    'Professional Summary',
    'Work Experience',
    'Technical Skills',
    'Projects',
    'Career Objective',
    'Education Description'
]

def clamp(v):
    try:
        return max(0, min(100, int(float(v))))
    except Exception:
        return 0

def allowed_file(filename, content_bytes=b''):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in ('pdf', 'docx'):
        return None, 'Only PDF and DOCX files are allowed.'
    if content_bytes:
        if ext == 'pdf' and not content_bytes.startswith(b'%PDF'):
            return None, 'File content does not match PDF format.'
        if ext == 'docx' and not content_bytes.startswith(b'PK'):
            return None, 'File content does not match DOCX format.'
    return ext, None


# ============================================================================
# Auth Endpoints
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'ResumeXpert AI API', 'time': datetime.now(timezone.utc).isoformat()})

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or request.form
    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    first_name = (data.get('first_name') or '').strip()
    last_name = (data.get('last_name') or '').strip()

    if not username or len(username) < 3 or len(username) > 150:
        return jsonify({'error': 'Username must be between 3 and 150 characters.'}), 400

    if not email:
        return jsonify({'error': 'Email is required.'}), 400
    try:
        valid = validate_email(email, check_deliverability=False)
        email = valid.normalized
    except EmailNotValidError as e:
        return jsonify({'error': f'Invalid email address: {str(e)}'}), 400

    if not password or len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters long.'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username is already taken.'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email is already registered.'}), 400

    user = User(
        username=username,
        email=email,
        first_name=first_name,
        last_name=last_name
    )
    user.set_password(password)
    db.session.add(user)
    db.session.flush()

    profile = Profile(user_id=user.id)
    db.session.add(profile)
    db.session.commit()

    login_user(user)
    token = generate_token(user.id)

    return jsonify({
        'message': 'Account registered successfully.',
        'token': token,
        'user': user.to_dict(include_profile=True)
    }), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or request.form
    identifier = (data.get('username') or data.get('email') or '').strip()
    password = data.get('password') or ''

    if not identifier or not password:
        return jsonify({'error': 'Username/email and password are required.'}), 400

    user = User.query.filter(
        (User.username == identifier) | (User.email == identifier.lower())
    ).first()

    if not user or not user.check_password(password):
        return jsonify({'error': 'Username or password is not correct.'}), 401

    login_user(user)
    token = generate_token(user.id)

    return jsonify({
        'message': 'Logged in successfully.',
        'token': token,
        'user': user.to_dict(include_profile=True)
    })

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    logout_user()
    return jsonify({'message': 'Logged out successfully.'})

@app.route('/api/auth/me', methods=['GET'])
@login_required
def me():
    if not current_user.profile:
        prof = Profile(user_id=current_user.id)
        db.session.add(prof)
        db.session.commit()

    n_resumes = Resume.query.filter_by(user_id=current_user.id).count()
    n_analyses = sum(M.query.join(Resume).filter(Resume.user_id == current_user.id).count() for M, *_ in KINDS.values())

    return jsonify({
        'user': current_user.to_dict(include_profile=True),
        'stats': {
            'resumes_count': n_resumes,
            'analyses_count': n_analyses
        }
    })

@app.route('/api/auth/profile', methods=['PUT'])
@login_required
def update_profile():
    data = request.get_json(silent=True) or request.form
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    email = data.get('email')

    if first_name is not None:
        current_user.first_name = str(first_name).strip()
    if last_name is not None:
        current_user.last_name = str(last_name).strip()

    if email:
        email = str(email).strip().lower()
        try:
            valid = validate_email(email, check_deliverability=False)
            email = valid.normalized
        except EmailNotValidError as e:
            return jsonify({'error': f'Invalid email: {str(e)}'}), 400

        existing = User.query.filter_by(email=email).first()
        if existing and existing.id != current_user.id:
            return jsonify({'error': 'This email address is already in use.'}), 400
        current_user.email = email

    prof = Profile.query.filter_by(user_id=current_user.id).first()
    if not prof:
        prof = Profile(user_id=current_user.id)
        db.session.add(prof)

    if 'phone' in data:
        prof.phone = str(data.get('phone') or '').strip()
    if 'target_role' in data:
        prof.target_role = str(data.get('target_role') or '').strip()
    if 'bio' in data:
        prof.bio = str(data.get('bio') or '').strip()

    db.session.commit()
    return jsonify({
        'message': 'Profile updated successfully.',
        'user': current_user.to_dict(include_profile=True)
    })


# ============================================================================
# Resume CRUD Endpoints
# ============================================================================

@app.route('/api/resumes', methods=['GET'])
@login_required
def list_resumes():
    resumes = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.created.desc()).all()
    return jsonify([r.to_dict() for r in resumes])

@app.route('/api/resumes/upload', methods=['POST'])
@login_required
def upload_resume():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in request.'}), 400

    f = request.files['file']
    if not f or not f.filename:
        return jsonify({'error': 'Please select a file to upload.'}), 400

    head = f.read(4)
    f.seek(0)
    ext, err = allowed_file(f.filename, head)
    if err:
        return jsonify({'error': err}), 400

    # Check file size
    f.seek(0, os.SEEK_END)
    size = f.tell()
    f.seek(0)
    max_bytes = app.config['MAX_UPLOAD_MB'] * 1024 * 1024
    if size > max_bytes:
        return jsonify({'error': f'File exceeds maximum size of {app.config["MAX_UPLOAD_MB"]} MB.'}), 400

    folder = os.path.join(app.config['MEDIA_ROOT'], 'resumes', str(current_user.id))
    os.makedirs(folder, exist_ok=True)
    unique_name = f'{uuid.uuid4().hex}.{ext}'
    fpath = os.path.join(folder, unique_name)
    f.save(fpath)

    raw_title = request.form.get('title', '').strip()
    title = raw_title[:150] if raw_title else f.filename[:150]

    resume = Resume(user_id=current_user.id, title=title, file_path=fpath)
    db.session.add(resume)
    db.session.flush()

    try:
        resume.text = extract_text(fpath).strip()
    except Exception as e:
        resume.text = ''

    if len(resume.text) < 50:
        if os.path.exists(fpath):
            try:
                os.remove(fpath)
            except OSError:
                pass
        db.session.rollback()
        return jsonify({
            'error': 'Could not extract readable text (scanned, image-only or corrupt file). Please upload a text-based PDF or DOCX.'
        }), 400

    db.session.commit()
    return jsonify({
        'message': 'Resume uploaded and text extracted successfully.',
        'resume': resume.to_dict(include_text=False)
    }), 201

@app.route('/api/resumes/<int:pk>/text', methods=['GET'])
@login_required
def get_resume_text(pk):
    r = Resume.query.filter_by(id=pk, user_id=current_user.id).first_or_404(
        description=f'Resume #{pk} not found.'
    )
    return jsonify({
        'id': r.id,
        'title': r.title,
        'word_count': r.word_count,
        'text': r.text
    })

@app.route('/api/resumes/<int:pk>/file', methods=['GET'])
@login_required
def download_resume_file(pk):
    r = Resume.query.filter_by(id=pk, user_id=current_user.id).first_or_404(
        description=f'Resume #{pk} not found.'
    )
    if not os.path.exists(r.file_path):
        return jsonify({'error': 'File not found on server disk.'}), 404

    ext = r.file_path.rsplit('.', 1)[-1].lower()
    return send_file(
        r.file_path,
        download_name=f'{r.title}.{ext}',
        as_attachment=False
    )

@app.route('/api/resumes/<int:pk>', methods=['DELETE'])
@login_required
def delete_resume(pk):
    r = Resume.query.filter_by(id=pk, user_id=current_user.id).first_or_404(
        description=f'Resume #{pk} not found.'
    )
    if os.path.exists(r.file_path):
        try:
            os.remove(r.file_path)
        except OSError:
            pass
    db.session.delete(r)
    db.session.commit()
    return jsonify({'message': f'Resume "{r.title}" deleted successfully.'})


# ============================================================================
# Analysis Endpoints
# ============================================================================

@app.route('/api/analysis/run/<kind>', methods=['POST'])
@login_required
def run_analysis(kind):
    if kind not in KINDS:
        return jsonify({'error': f'Invalid analysis kind "{kind}". Allowed: {list(KINDS.keys())}'}), 400

    data = request.get_json(silent=True) or request.form
    rid = data.get('resume_id') or data.get('resume')

    try:
        rid = int(rid)
    except (ValueError, TypeError):
        return jsonify({'error': 'Valid resume_id is required.'}), 400

    resume = Resume.query.filter_by(id=rid, user_id=current_user.id).first()
    if not resume:
        return jsonify({'error': 'Selected resume not found.'}), 404

    if not resume.text or len(resume.text.strip()) < 50:
        return jsonify({'error': 'Resume text is too short or empty.'}), 400

    try:
        if kind == 'analysis':
            res_dict = nlp.analyze(resume.text)
            obj = ResumeAnalysis(
                resume_id=resume.id,
                score=clamp(res_dict.get('overall', 0)),
                data=res_dict
            )
            db.session.add(obj)

        elif kind == 'ats':
            rule = ats_rules(resume.text)
            ai = nlp.ats_semantic(resume.text)
            score = round(0.6 * rule['score'] + 0.4 * clamp(ai.get('score', 0)))
            status = 'Excellent' if score >= 80 else 'Good - minor fixes needed' if score >= 60 else 'Needs significant work'
            combined = {**ai, 'rule': rule, 'status': status}
            obj = ATSAnalysis(
                resume_id=resume.id,
                score=score,
                data=combined
            )
            db.session.add(obj)

        elif kind == 'match':
            job_desc = (data.get('job_description') or '').strip()[:8000]
            if len(job_desc) < 50:
                return jsonify({'error': 'Please provide a fuller job description (at least 50 characters).'}), 400

            job_title = (data.get('job_title') or '').strip()[:150]
            res_dict = nlp.match_job(resume.text, job_desc)
            obj = JobMatch(
                resume_id=resume.id,
                score=clamp(res_dict.get('match_percent', 0)),
                job_title=job_title,
                job_description=job_desc,
                data=res_dict
            )
            db.session.add(obj)

        elif kind == 'improve':
            section = (data.get('section') or '').strip()
            if section not in SECTIONS:
                return jsonify({'error': f'Invalid section. Allowed: {SECTIONS}'}), 400

            orig = (data.get('original') or '').strip()[:4000]
            facts = (data.get('facts') or '').strip()[:2000]
            res_dict = nlp.improve(resume.text, section, orig, facts)
            obj = Improvement(
                resume_id=resume.id,
                section=section,
                original=str(res_dict.get('original') or orig),
                data=res_dict
            )
            db.session.add(obj)

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Analysis error: {str(e)}'}), 500

    return jsonify({
        'id': obj.id,
        'kind': kind,
        'resume_id': resume.id,
        'resume_title': resume.title,
        'score': obj.score,
        'engine': obj.data.get('engine', 'sklearn') if isinstance(obj.data, dict) else 'sklearn',
        'data': obj.data,
        'created': obj.created.isoformat() if obj.created else None
    })

@app.route('/api/jobs/recommend', methods=['POST'])
@login_required
def recommend_jobs_api():
    data = request.get_json(silent=True) or request.form or {}
    rid = data.get('resume_id') or data.get('resume')
    resume_text = ''
    resume_title = 'Resume'

    if rid:
        try:
            rid = int(rid)
            resume = Resume.query.filter_by(id=rid, user_id=current_user.id).first()
            if resume:
                resume_text = resume.text or ''
                resume_title = resume.title or 'Resume'
        except (ValueError, TypeError):
            pass

    if not resume_text:
        resume_text = (data.get('resume_text') or '').strip()

    if not resume_text or len(resume_text.strip()) < 50:
        return jsonify({'error': 'Please select a valid resume or provide at least 50 characters of resume text.'}), 400

    preferences = {
        'location': (data.get('location') or '').strip(),
        'experience_level': (data.get('experience_level') or '').strip(),
        'industry': (data.get('industry') or '').strip()
    }

    try:
        res_dict = nlp.recommend_jobs(resume_text, preferences)
        return jsonify({
            'success': True,
            'resume_title': resume_title,
            'result': res_dict
        })
    except Exception as e:
        return jsonify({'error': f'Job recommendation error: {str(e)}'}), 500

@app.route('/api/analysis/history', methods=['GET'])
@login_required
def analysis_history():
    rows = []
    for k, (ModelClass, label, _) in KINDS.items():
        records = ModelClass.query.join(Resume).filter(Resume.user_id == current_user.id).all()
        for o in records:
            rows.append({
                'id': o.id,
                'kind': k,
                'label': label,
                'resume_id': o.resume_id,
                'resume_title': o.resume.title,
                'score': o.score,
                'created': o.created.isoformat() if o.created else None
            })

    rows.sort(key=lambda x: x['created'] or '', reverse=True)
    return jsonify(rows)

@app.route('/api/analysis/<kind>/<int:aid>', methods=['GET'])
@login_required
def get_analysis_result(kind, aid):
    if kind not in KINDS:
        return jsonify({'error': f'Invalid kind "{kind}".'}), 400

    ModelClass, label, _ = KINDS[kind]
    obj = ModelClass.query.join(Resume).filter(
        ModelClass.id == aid,
        Resume.user_id == current_user.id
    ).first_or_404(description=f'{label} result #{aid} not found.')

    resp = {
        'id': obj.id,
        'kind': kind,
        'label': label,
        'resume_id': obj.resume_id,
        'resume_title': obj.resume.title,
        'score': obj.score,
        'engine': obj.data.get('engine', 'sklearn') if isinstance(obj.data, dict) else 'sklearn',
        'data': obj.data,
        'created': obj.created.isoformat() if obj.created else None
    }
    if kind == 'match':
        resp['job_title'] = obj.job_title
        resp['job_description'] = obj.job_description
    elif kind == 'improve':
        resp['section'] = obj.section
        resp['original'] = obj.original

    return jsonify(resp)

@app.route('/api/dashboard', methods=['GET'])
@login_required
def dashboard_stats():
    u = current_user
    an_list = ResumeAnalysis.query.join(Resume).filter(Resume.user_id == u.id).order_by(ResumeAnalysis.created.asc()).all()
    ats_list = ATSAnalysis.query.join(Resume).filter(Resume.user_id == u.id).order_by(ATSAnalysis.created.asc()).all()
    total_analyses = sum(M.query.join(Resume).filter(Resume.user_id == u.id).count() for M, *_ in KINDS.values())
    resumes_count = Resume.query.filter_by(user_id=u.id).count()

    matches = JobMatch.query.join(Resume).filter(Resume.user_id == u.id).order_by(JobMatch.created.desc()).limit(5).all()
    recent_resumes = Resume.query.filter_by(user_id=u.id).order_by(Resume.created.desc()).limit(5).all()

    chart = {
        'an': [a.score for a in an_list][-12:],
        'ats': [a.score for a in ats_list][-12:]
    }

    return jsonify({
        'user': u.to_dict(include_profile=True),
        'n_resumes': resumes_count,
        'n_analyses': total_analyses,
        'last_an': an_list[-1].score if an_list else None,
        'last_ats': ats_list[-1].score if ats_list else None,
        'chart': chart,
        'matches': [
            {
                'id': m.id,
                'job_title': m.job_title or 'Job Match',
                'resume_title': m.resume.title,
                'score': m.score,
                'created': m.created.isoformat() if m.created else None
            } for m in matches
        ],
        'recent_resumes': [
            {
                'id': r.id,
                'title': r.title,
                'word_count': r.word_count,
                'created': r.created.isoformat() if r.created else None
            } for r in recent_resumes
        ]
    })


# Create tables on startup
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='127.0.0.1', port=port, debug=True)
