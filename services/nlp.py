"""
NLP Analysis Engine:
- Primary: Google Gemini AI (via google-genai) when GEMINI_API_KEY is configured.
- Fallback: scikit-learn TF-IDF + cosine similarity rule-based engine.
"""
import os
import re
import json
import math
import logging
from collections import Counter

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False

logger = logging.getLogger(__name__)

STOPWORDS = {'and','or','the','a','an','to','of','in','for','on','with','at','by','from','is','are',
             'was','were','be','been','being','have','has','had','do','does','did','will','would',
             'could','should','may','might','shall','i','we','you','they','he','she','it','this',
             'that','these','those','my','your','our','their','his','her','its'}

def _get_groq_api_key():
    """Retrieve Groq API key if GROQ_API_KEY is available."""
    api_key = os.getenv('GROQ_API_KEY', '').strip()
    if not api_key:
        try:
            from config import Config
            api_key = getattr(Config, 'GROQ_API_KEY', '').strip()
        except Exception:
            api_key = ''
    if not api_key or api_key in ('your-groq-api-key-here', 'your_groq_api_key_here'):
        return None
    return api_key

def _call_groq(prompt):
    """Call Groq with JSON output format using fast LLMs."""
    api_key = _get_groq_api_key()
    if not api_key:
        return None, None

    import urllib.request
    import urllib.error
    models = ['openai/gpt-oss-120b', 'qwen/qwen3.8-27b', 'openai/gpt-oss-20b', 'llama-3.3-70b-versatile', 'llama-3.1-8b-instant']
    for m in models:
        try:
            req = urllib.request.Request(
                'https://api.groq.com/openai/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                    'User-Agent': 'ResumeXpert-AI'
                },
                data=json.dumps({
                    'model': m,
                    'messages': [
                        {
                            'role': 'system',
                            'content': 'You are an expert executive recruiter, resume analyst, and ATS specialist. Always respond strictly with a valid JSON object matching the requested schema, with no markdown fences, no preamble, and no extra commentary.'
                        },
                        {
                            'role': 'user',
                            'content': prompt
                        }
                    ],
                    'response_format': {'type': 'json_object'},
                    'temperature': 0.2
                }).encode('utf-8')
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                raw_text = data['choices'][0]['message']['content']
                parsed = _parse_json(raw_text)
                if parsed:
                    return parsed, f"Groq AI ({m})"
        except Exception as err:
            logger.warning(f"Groq call to {m} failed: {err}")
            continue
    return None, None

def _get_gemini_client():
    """Retrieve Gemini client if GEMINI_API_KEY is available."""
    api_key = os.getenv('GEMINI_API_KEY', '').strip()
    if not api_key:
        try:
            from config import Config
            api_key = getattr(Config, 'GEMINI_API_KEY', '').strip()
        except Exception:
            api_key = ''
    if not api_key or api_key in ('your-gemini-api-key-here', 'your_gemini_api_key_here'):
        return None, None
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        return client, api_key
    except Exception as e:
        logger.warning(f"Failed to initialize Gemini client: {e}")
        return None, None

def _call_gemini(prompt):
    """Call Gemini with JSON output format, trying 2.5-flash then 1.5-flash."""
    client, _ = _get_gemini_client()
    if not client:
        return None

    from google.genai import types
    models = ['gemini-3.8-flash', 'gemini-2.5-flash', 'gemini-2.0-flash']
    for m in models:
        try:
            response = client.models.generate_content(
                model=m,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2
                )
            )
            text = response.text if hasattr(response, 'text') else str(response)
            parsed = _parse_json(text)
            if parsed:
                return parsed
        except Exception as err:
            logger.warning(f"Gemini call to {m} failed: {err}")
            continue
    return None

def _call_llm(prompt):
    """Try Groq first (ultra-fast), fallback to Gemini, return (parsed_json, engine_id, engine_label)."""
    # 1. Groq AI
    groq_res, groq_label = _call_groq(prompt)
    if groq_res:
        return groq_res, 'groq', groq_label or 'Groq AI'

    # 2. Gemini AI
    gemini_res = _call_gemini(prompt)
    if gemini_res:
        return gemini_res, 'gemini', 'Google Gemini AI'

    return None, None, None

def _parse_json(text):
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith('```'):
        cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'\s*```$', '', cleaned, flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        start = cleaned.find('{')
        end = cleaned.rfind('}')
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(cleaned[start:end+1])
            except Exception:
                pass
    return None

def _keywords(text, n=30):
    """Extract top N keywords from text using TF-IDF or frequency fallback."""
    text_clean = re.sub(r'[^a-zA-Z0-9\s+#]', ' ', text.lower())
    words = [w for w in text_clean.split() if len(w) > 2 and w not in STOPWORDS]
    if not words:
        return []
    if SKLEARN_AVAILABLE:
        try:
            vec = TfidfVectorizer(ngram_range=(1, 2), max_features=200)
            vec.fit([' '.join(words)])
            scores = dict(zip(vec.get_feature_names_out(), vec.idf_))
            return sorted(scores, key=scores.get)[:n]
        except Exception:
            pass
    # Pure Python frequency-based keyword ranking
    counts = Counter(words)
    return [w for w, _ in counts.most_common(n)]

def _similarity(text1, text2):
    """Cosine similarity between two texts."""
    if SKLEARN_AVAILABLE:
        try:
            vec = TfidfVectorizer()
            tfidf = vec.fit_transform([text1, text2])
            return float(cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0])
        except Exception:
            pass
    # Pure Python vector cosine similarity
    w1 = Counter(re.findall(r'\w+', text1.lower()))
    w2 = Counter(re.findall(r'\w+', text2.lower()))
    inter = set(w1) & set(w2)
    num = sum(w1[x] * w2[x] for x in inter)
    d1 = math.sqrt(sum(v**2 for v in w1.values()))
    d2 = math.sqrt(sum(v**2 for v in w2.values()))
    return float(num / (d1 * d2)) if d1 and d2 else 0.0

# ============================================================================
# 1. Resume Analysis
# ============================================================================

def analyze(resume_text):
    """Analyze resume using Gemini AI when configured, else TF-IDF rule engine."""
    prompt = f"""You are a world-class Executive Technical Recruiter and ATS Specialist.
Analyze the following resume thoroughly and provide actionable, objective scoring and feedback.
Resume text:
\"\"\"{resume_text[:12000]}\"\"\"

Return a valid JSON object strictly matching this schema:
{{
  "overall": <integer 0-100>,
  "scores": {{
    "skills": <integer 0-100>,
    "education": <integer 0-100>,
    "experience": <integer 0-100>,
    "formatting": <integer 0-100>,
    "grammar": <integer 0-100>,
    "summary": <integer 0-100>
  }},
  "sections": {{
    "summary": "Detected" or "Not detected",
    "experience": "Detected" or "Not detected",
    "education": "Detected" or "Not detected",
    "skills": "Detected" or "Not detected",
    "projects": "Detected" or "Not detected",
    "certifications": "Detected" or "Not detected"
  }},
  "strengths": [<list of 3-5 specific bullet strengths>],
  "weaknesses": [<list of 2-4 critical areas needing improvement>],
  "missing": [<list of missing sections or elements>],
  "improvements": [<list of 3-5 high-impact actionable recommendations>],
  "keywords": [<list of 15-25 top technical and domain skills/keywords found>],
  "feedback": "<concise 2-3 sentence executive summary of resume performance>"
}}
"""
    ai_result, engine_id, engine_label = _call_llm(prompt)
    if ai_result and isinstance(ai_result, dict) and 'overall' in ai_result:
        try:
            return {
                'engine': engine_id,
                'engine_label': engine_label,
                'overall': max(0, min(100, int(ai_result.get('overall', 75)))),
                'scores': {
                    'skills': max(0, min(100, int(ai_result.get('scores', {}).get('skills', 70)))),
                    'education': max(0, min(100, int(ai_result.get('scores', {}).get('education', 70)))),
                    'experience': max(0, min(100, int(ai_result.get('scores', {}).get('experience', 70)))),
                    'formatting': max(0, min(100, int(ai_result.get('scores', {}).get('formatting', 75)))),
                    'grammar': max(0, min(100, int(ai_result.get('scores', {}).get('grammar', 85)))),
                    'summary': max(0, min(100, int(ai_result.get('scores', {}).get('summary', 60)))),
                },
                'sections': ai_result.get('sections', {}),
                'strengths': ai_result.get('strengths', []),
                'weaknesses': ai_result.get('weaknesses', []),
                'missing': ai_result.get('missing', []),
                'improvements': ai_result.get('improvements', []),
                'keywords': ai_result.get('keywords', _keywords(resume_text, 20)),
                'feedback': ai_result.get('feedback', 'AI Resume Analysis completed successfully.')
            }
        except Exception as e:
            logger.warning(f"Error sanitizing Gemini analysis result: {e}")

    # Fallback to local rule-based / TF-IDF engine
    return _local_analyze(resume_text)

def _local_analyze(resume_text):
    text = resume_text.lower()
    words = resume_text.split()
    word_count = len(words)

    sections = {
        'summary': bool(re.search(r'summary|objective|profile', text)),
        'experience': bool(re.search(r'experience|employment|work history', text)),
        'education': bool(re.search(r'education|university|college|degree|bachelor|master', text)),
        'skills': bool(re.search(r'skills|technologies|competenc', text)),
        'projects': bool(re.search(r'projects|portfolio', text)),
        'certifications': bool(re.search(r'certif|certification', text)),
    }

    has_email = bool(re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', resume_text))
    has_phone = bool(re.search(r'(\+?\d[\d\s().-]{8,}\d)', resume_text))
    has_linkedin = bool(re.search(r'linkedin', text))
    has_github = bool(re.search(r'github', text))

    s_score = sum(sections.values()) / len(sections) * 100
    exp_score = 70 if sections['experience'] else 30
    edu_score = 80 if sections['education'] else 40
    skill_score = 85 if sections['skills'] else 35
    fmt_score = 60 + (10 if has_email else 0) + (10 if has_phone else 0) + (10 if 250 <= word_count <= 1200 else 0) + (10 if sections['projects'] else 0)
    grammar_score = 75
    summary_score = 80 if sections['summary'] else 30

    overall = int(0.2*s_score + 0.2*exp_score + 0.15*edu_score + 0.15*skill_score + 0.15*fmt_score + 0.1*grammar_score + 0.05*summary_score)
    keywords = _keywords(resume_text, 20)
    strengths, weaknesses, missing, improvements = [], [], [], []

    if sections['experience']: strengths.append('Work experience section is present.')
    if sections['education']: strengths.append('Education section is present.')
    if sections['skills']: strengths.append('Skills section detected.')
    if has_email and has_phone: strengths.append('Contact information (email & phone) found.')
    if sections['projects']: strengths.append('Projects section adds value.')
    if has_linkedin: strengths.append('LinkedIn profile mentioned.')
    if has_github: strengths.append('GitHub profile mentioned.')

    if not sections['summary']: weaknesses.append('No professional summary or objective found.')
    if not sections['certifications']: weaknesses.append('No certifications listed.')
    if not has_linkedin: weaknesses.append('LinkedIn profile not mentioned.')
    if not has_github: weaknesses.append('GitHub profile not mentioned.')
    if word_count < 200: weaknesses.append(f'Resume is short ({word_count} words); aim for 300-700 words.')
    if word_count > 1500: weaknesses.append(f'Resume may be too long ({word_count} words).')

    if not sections['summary']: missing.append('Professional Summary / Career Objective')
    if not sections['certifications']: missing.append('Certifications / Courses')
    if not sections['projects']: missing.append('Projects section')

    improvements.append('Use strong action verbs (e.g., Developed, Led, Implemented, Optimized).')
    improvements.append('Quantify achievements with numbers where possible.')
    improvements.append('Tailor resume keywords to match the target job description.')
    if not has_linkedin: improvements.append('Add your LinkedIn profile URL.')
    if not has_github: improvements.append('Add your GitHub profile URL.')

    return {
        'engine': 'sklearn',
        'engine_label': 'scikit-learn (Offline Engine)',
        'overall': overall,
        'scores': {'skills': int(skill_score), 'education': int(edu_score), 'experience': int(exp_score),
                   'formatting': int(fmt_score), 'grammar': grammar_score, 'summary': int(summary_score)},
        'sections': {k: ('Detected' if v else 'Not detected') for k, v in sections.items()},
        'strengths': strengths,
        'weaknesses': weaknesses,
        'missing': missing,
        'improvements': improvements,
        'keywords': keywords,
        'feedback': f'Your resume scored {overall}/100. Focus on: {", ".join(weaknesses[:2]) if weaknesses else "great job!"}',
    }

# ============================================================================
# 2. ATS Semantic Checker
# ============================================================================

def ats_semantic(resume_text):
    """Semantic ATS evaluation using Gemini AI, with TF-IDF fallback."""
    prompt = f"""You are an ATS (Applicant Tracking System) parsing and optimization engine.
Analyze the following resume for ATS readability, keyword density, and formatting issues:
\"\"\"{resume_text[:12000]}\"\"\"

Return a valid JSON object strictly matching this schema:
{{
  "score": <integer 0-100 indicating ATS friendliness>,
  "semantic_issues": [<list of specific ATS issues, e.g. lack of industry standard keywords, ambiguous dates, complex phrasing>],
  "keyword_suggestions": [<list of 5-10 critical keywords this candidate should consider adding>],
  "recommendations": [<list of 3-5 best practices for ATS readability>]
}}
"""
    ai_result, engine_id, engine_label = _call_llm(prompt)
    if ai_result and isinstance(ai_result, dict) and 'score' in ai_result:
        try:
            return {
                'engine': engine_id,
                'engine_label': engine_label,
                'score': max(0, min(100, int(ai_result.get('score', 75)))),
                'semantic_issues': ai_result.get('semantic_issues', []),
                'keyword_suggestions': ai_result.get('keyword_suggestions', []),
                'recommendations': ai_result.get('recommendations', [])
            }
        except Exception:
            pass

    # Fallback
    text = resume_text.lower()
    ats_keywords = ['python','java','javascript','sql','management','leadership','communication',
                    'teamwork','agile','scrum','machine learning','data','analysis','development',
                    'design','testing','documentation','problem solving','bachelor','master']
    found_kw = [k for k in ats_keywords if k in text]
    score = min(100, 50 + len(found_kw) * 3)
    semantic_issues = []
    if len(found_kw) < 5: semantic_issues.append('Low keyword density for ATS scanners.')
    if not re.search(r'summary|objective', text): semantic_issues.append('Missing career summary or objective statement.')
    return {
        'engine': 'sklearn',
        'engine_label': 'scikit-learn (Offline Engine)',
        'score': score,
        'semantic_issues': semantic_issues,
        'keyword_suggestions': [k for k in ats_keywords if k not in text][:8],
        'recommendations': ['Use industry-standard keywords from job postings.',
                            'Keep formatting simple — avoid tables and complex layouts.',
                            'Use standard section headings (Experience, Education, Skills).'],
    }

# ============================================================================
# 3. Job Description Matching
# ============================================================================

def match_job(resume_text, job_text):
    """Match resume to job description using Gemini AI, with TF-IDF fallback."""
    prompt = f"""Compare this candidate's resume with the target job description.
Resume:
\"\"\"{resume_text[:8000]}\"\"\"

Job Description:
\"\"\"{job_text[:4000]}\"\"\"

Return a valid JSON object strictly matching this schema:
{{
  "match_percent": <integer 0-100 reflecting true fit>,
  "required_skills": [<list of top 10-15 skills required by the job>],
  "matching_skills": [<list of skills present in both resume and job>],
  "missing_skills": [<list of required job skills missing from the resume>],
  "experience_comparison": "<1-2 sentence assessment of work experience alignment>",
  "education_comparison": "<1-2 sentence assessment of education/qualifications alignment>",
  "relevant_experience": [<list of 3-5 most relevant candidate strengths for this role>],
  "missing_qualifications": [<list of 2-5 major gaps or unaddressed job requirements>],
  "keywords": [<list of 10 primary keywords from the job description>],
  "suggestions": [<list of 3-4 specific suggestions to increase match score for this role>]
}}
"""
    ai_result, engine_id, engine_label = _call_llm(prompt)
    if ai_result and isinstance(ai_result, dict) and 'match_percent' in ai_result:
        try:
            return {
                'engine': engine_id,
                'engine_label': engine_label,
                'match_percent': max(0, min(100, int(ai_result.get('match_percent', 50)))),
                'required_skills': ai_result.get('required_skills', []),
                'matching_skills': ai_result.get('matching_skills', []),
                'missing_skills': ai_result.get('missing_skills', []),
                'experience_comparison': ai_result.get('experience_comparison', 'Experience evaluated against job description.'),
                'education_comparison': ai_result.get('education_comparison', 'Education evaluated against job requirements.'),
                'relevant_experience': ai_result.get('relevant_experience', []),
                'missing_qualifications': ai_result.get('missing_qualifications', []),
                'keywords': ai_result.get('keywords', []),
                'suggestions': ai_result.get('suggestions', [])
            }
        except Exception:
            pass

    # Fallback to TF-IDF
    sim = _similarity(resume_text, job_text)
    match_percent = int(sim * 100)
    resume_kw = set(_keywords(resume_text, 40))
    job_kw = set(_keywords(job_text, 40))
    matching = list(resume_kw & job_kw)
    missing = list(job_kw - resume_kw)
    required = list(job_kw)[:20]

    return {
        'engine': 'sklearn',
        'engine_label': 'scikit-learn (Offline Engine)',
        'match_percent': match_percent,
        'required_skills': required[:15],
        'matching_skills': matching[:15],
        'missing_skills': missing[:15],
        'experience_comparison': 'Your resume covers some of the required experience. Add more relevant details.',
        'education_comparison': 'Education match depends on specific requirements. Review the job posting.',
        'relevant_experience': matching[:5],
        'missing_qualifications': missing[:8],
        'keywords': required[:10],
        'suggestions': [
            f'Add missing keywords: {", ".join(missing[:5])}' if missing else 'Good keyword coverage!',
            'Mirror the language used in the job description.',
            'Quantify your achievements to stand out.',
            f'Your resume matches {match_percent}% of job keywords.',
        ],
    }

# ============================================================================
# 4. Resume Section Improvement
# ============================================================================

def improve(resume_text, section, original_text, facts):
    """Provide AI-powered rewrite and suggestions for a resume section."""
    text_to_improve = original_text or resume_text[:2000]
    prompt = f"""You are a professional executive resume writer.
Rewrite and elevate the following \"{section}\" section of a resume to sound impactful, metrics-driven, and ATS-friendly.
Original Section Text:
\"\"\"{text_to_improve}\"\"\"

Additional Facts / Notes from candidate:
\"\"\"{facts or 'None provided'}\"\"\"

Return a valid JSON object strictly matching this schema:
{{
  "improved": "<complete, professionally polished, rewritten text for this section>",
  "changes": [<list of 3-4 bullet explanations of specific changes and improvements made>],
  "action_verbs": [<list of 5-8 strong action verbs used in the rewrite>],
  "recommended_skills": [<list of 5-8 relevant skills recommended for this section>],
  "notes": "<advice on tailoring this section for higher impact>"
}}
"""
    ai_result, engine_id, engine_label = _call_llm(prompt)
    if ai_result and isinstance(ai_result, dict) and 'improved' in ai_result:
        try:
            return {
                'engine': engine_id,
                'engine_label': engine_label,
                'original': original_text or f'[{section} section from your resume]',
                'improved': ai_result.get('improved', ''),
                'changes': ai_result.get('changes', []),
                'action_verbs': ai_result.get('action_verbs', []),
                'recommended_skills': ai_result.get('recommended_skills', []),
                'notes': ai_result.get('notes', f'{engine_label} polished your {section} section.')
            }
        except Exception:
            pass

    # Fallback
    keywords = _keywords(text_to_improve, 10)
    action_verbs = ['Developed', 'Led', 'Implemented', 'Designed', 'Managed', 'Optimized',
                    'Built', 'Created', 'Delivered', 'Analyzed', 'Improved', 'Collaborated']
    suggestions = [
        f'Start bullets with strong action verbs: {", ".join(action_verbs[:5])}.',
        'Quantify achievements (e.g., "Increased efficiency by 30%").',
        'Focus on impact and results, not just tasks.',
        'Keep sentences concise and to the point.',
    ]
    if facts:
        suggestions.insert(0, f'Incorporate these facts: {facts[:200]}')
    return {
        'engine': 'sklearn',
        'engine_label': 'scikit-learn (Offline Engine)',
        'original': original_text or f'[{section} section from your resume]',
        'improved': (original_text or '') + '\n\n[Rewrite tip: ' + suggestions[0] + ']',
        'changes': suggestions,
        'action_verbs': action_verbs,
        'recommended_skills': keywords[:8],
        'notes': f'Focus on improving your {section} by using the suggestions above. Keyword analysis found: {", ".join(keywords[:5])}',
    }
