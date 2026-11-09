import os, uuid, re
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, abort, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from config import Config
from models import db, User, Profile, Resume, ResumeAnalysis, ATSAnalysis, JobMatch, Improvement
from forms import LoginForm, RegisterForm, UserForm, ProfileForm
from services.extract import extract_text
from services.rules import ats_rules
from services import nlp

load_dotenv()
app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
csrf = CSRFProtect(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(uid):
    return User.query.get(int(uid))

KINDS = {
    'analysis': (ResumeAnalysis, 'Resume Analysis', 'Get a score with strengths, weaknesses and detailed feedback.'),
    'ats': (ATSAnalysis, 'ATS Compatibility Checker', 'Rule-based formatting checks plus TF-IDF keyword evaluation.'),
    'match': (JobMatch, 'Job Description Matching', 'Paste a job description and see how well your resume fits.'),
    'improve': (Improvement, 'Resume Improvement Suggestions', 'Get keyword and structure suggestions to improve your resume.'),
}
SECTIONS = ['Professional Summary', 'Work Experience', 'Technical Skills', 'Projects', 'Career Objective', 'Education Description']

def clamp(v):
    try: return max(0, min(100, int(float(v))))
    except: return 0

def allowed_file(f):
    ext = f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else ''
    if ext not in ('pdf', 'docx'):
        return None, 'Only PDF and DOCX files are allowed.'
    if f.content_length and f.content_length > app.config['MAX_UPLOAD_MB'] * 1024 * 1024:
        return None, f'File is larger than {app.config["MAX_UPLOAD_MB"]} MB.'
    head = f.read(4); f.seek(0)
    if (ext == 'pdf' and head != b'%PDF') or (ext == 'docx' and head[:2] != b'PK'):
        return None, 'File content does not match its extension.'
    return ext, None

@app.route('/')
def landing():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data.lower())
        user.set_password(form.password1.data)
        db.session.add(user)
        db.session.flush()
        db.session.add(Profile(user_id=user.id))
        db.session.commit()
        login_user(user)
        flash('Welcome! Your account has been created.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('accounts/register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(request.args.get('next') or url_for('dashboard'))
        flash('Invalid username or password.', 'danger')
    return render_template('accounts/login.html', form=form)

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('landing'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    prof = Profile.query.filter_by(user_id=current_user.id).first()
    if prof is None:
        prof = Profile(user_id=current_user.id)
        db.session.add(prof)
        db.session.commit()
    uf = UserForm(obj=current_user)
    pf = ProfileForm(obj=prof)
    if request.method == 'POST':
        uf = UserForm(request.form, obj=current_user)
        pf = ProfileForm(request.form, obj=prof)
        if uf.validate() and pf.validate():
            uf.populate_obj(current_user)
            pf.populate_obj(prof)
            db.session.commit()
            flash('Profile updated.', 'success')
            return redirect(url_for('profile'))
    return render_template('accounts/profile.html', uf=uf, pf=pf)

@app.route('/dashboard')
@login_required
def dashboard():
    u = current_user
    an = ResumeAnalysis.query.join(Resume).filter(Resume.user_id == u.id).order_by(ResumeAnalysis.created).all()
    ats_list = ATSAnalysis.query.join(Resume).filter(Resume.user_id == u.id).order_by(ATSAnalysis.created).all()
    total = sum(M.query.join(Resume).filter(Resume.user_id == u.id).count() for M, *_ in KINDS.values())
    matches = JobMatch.query.join(Resume).filter(Resume.user_id == u.id).order_by(JobMatch.created.desc()).limit(5).all()
    recent = Resume.query.filter_by(user_id=u.id).order_by(Resume.created.desc()).limit(5).all()
    chart = {'an': [a.score for a in an][-12:], 'ats': [a.score for a in ats_list][-12:]}
    return render_template('dashboard.html',
        n_resumes=Resume.query.filter_by(user_id=u.id).count(),
        n_analyses=total, last_an=an[-1].score if an else None,
        last_ats=ats_list[-1].score if ats_list else None,
        matches=matches, recent=recent, chart=chart)

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        f = request.files.get('file')
        if not f or not f.filename:
            flash('Please choose a file.', 'danger')
        else:
            ext, err = allowed_file(f)
            if err:
                flash(err, 'danger')
            else:
                fname = uuid.uuid4().hex + '.' + ext
                folder = os.path.join(app.config['MEDIA_ROOT'], 'resumes', str(current_user.id))
                os.makedirs(folder, exist_ok=True)
                fpath = os.path.join(folder, fname)
                f.save(fpath)
                title = (request.form.get('title') or f.filename)[:150]
                res = Resume(user_id=current_user.id, title=title, file_path=fpath)
                db.session.add(res)
                db.session.flush()
                try:
                    res.text = extract_text(fpath).strip()
                except Exception:
                    res.text = ''
                if len(res.text) < 50:
                    os.remove(fpath)
                    db.session.rollback()
                    flash('Could not extract readable text (scanned/image-only or corrupt file).', 'danger')
                else:
                    db.session.commit()
                    flash('Resume uploaded and text extracted.', 'success')
        return redirect(url_for('upload'))
    resumes = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.created.desc()).all()
    return render_template('upload.html', resumes=resumes, max_mb=app.config['MAX_UPLOAD_MB'])

@app.route('/resume/<int:pk>/delete', methods=['POST'])
@login_required
def resume_delete(pk):
    r = Resume.query.filter_by(id=pk, user_id=current_user.id).first_or_404()
    if os.path.exists(r.file_path):
        os.remove(r.file_path)
    db.session.delete(r)
    db.session.commit()
    flash('Resume deleted.', 'success')
    return redirect(url_for('upload'))

@app.route('/resume/<int:pk>/file')
@login_required
def resume_file(pk):
    r = Resume.query.filter_by(id=pk, user_id=current_user.id).first_or_404()
    ext = r.file_path.rsplit('.', 1)[-1].lower()
    return send_file(r.file_path, download_name=f'{r.title}.{ext}', as_attachment=False)

@app.route('/resume/<int:pk>/text')
@login_required
def resume_text(pk):
    r = Resume.query.filter_by(id=pk, user_id=current_user.id).first_or_404()
    return jsonify({'title': r.title, 'text': r.text})

@app.route('/tool/<kind>')
@login_required
def tool(kind):
    if kind not in KINDS:
        abort(404)
    M, title, desc = KINDS[kind]
    loaded, sel = None, request.args.get('resume', '')
    rid = request.args.get('r', '')
    if rid.isdigit():
        o = M.query.join(Resume).filter(M.id == int(rid), Resume.user_id == current_user.id).first()
        if o:
            loaded = {'id': o.id, 'score': o.score, 'data': o.data}
            sel = str(o.resume_id)
    resumes = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.created.desc()).all()
    return render_template('tool.html', kind=kind, title=title, desc=desc,
                           loaded=loaded, sel=sel, resumes=resumes, sections=SECTIONS)

@app.route('/run/<kind>', methods=['POST'])
@login_required
def run(kind):
    if kind not in KINDS:
        abort(404)
    rid = request.form.get('resume', '')
    resume = Resume.query.filter_by(id=int(rid) if rid.isdigit() else 0, user_id=current_user.id).first_or_404()
    try:
        if kind == 'analysis':
            d = nlp.analyze(resume.text)
            obj = ResumeAnalysis(resume_id=resume.id, score=clamp(d.get('overall')), data=d)
            db.session.add(obj)
        elif kind == 'ats':
            rule = ats_rules(resume.text)
            ai = nlp.ats_semantic(resume.text)
            s = round(.6 * rule['score'] + .4 * clamp(ai.get('score')))
            status = 'Excellent' if s >= 80 else 'Good - minor fixes needed' if s >= 60 else 'Needs significant work'
            obj = ATSAnalysis(resume_id=resume.id, score=s, data={**ai, 'rule': rule, 'status': status})
            db.session.add(obj)
        elif kind == 'match':
            job = request.form.get('job_description', '').strip()[:8000]
            if len(job) < 50:
                return jsonify({'error': 'Please paste a fuller job description (at least 50 characters).'}), 400
            d = nlp.match_job(resume.text, job)
            obj = JobMatch(resume_id=resume.id, score=clamp(d.get('match_percent')), data=d,
                           job_title=request.form.get('job_title', '')[:150], job_description=job)
            db.session.add(obj)
        else:  # improve
            section = request.form.get('section', '')
            if section not in SECTIONS:
                return jsonify({'error': 'Choose a valid section.'}), 400
            orig = request.form.get('original', '').strip()[:4000]
            facts = request.form.get('facts', '').strip()[:2000]
            d = nlp.improve(resume.text, section, orig, facts)
            obj = Improvement(resume_id=resume.id, section=section, original=str(d.get('original') or orig), data=d)
            db.session.add(obj)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    return jsonify({'id': obj.id, 'score': obj.score, 'data': obj.data})

@app.route('/history')
@login_required
def history():
    rows = []
    for k, (M, label, _) in KINDS.items():
        for o in M.query.join(Resume).filter(Resume.user_id == current_user.id).all():
            rows.append({'kind': k, 'label': label, 'id': o.id, 'resume': o.resume.title,
                         'score': o.score, 'created': o.created})
    rows.sort(key=lambda x: x['created'], reverse=True)
    return render_template('history.html', rows=rows)

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
