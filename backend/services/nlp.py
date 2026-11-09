"""
NLP analysis using scikit-learn TF-IDF + cosine similarity.
Replaces Gemini AI as per FYDP proposal requirement.
"""
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

STOPWORDS = {'and','or','the','a','an','to','of','in','for','on','with','at','by','from','is','are',
             'was','were','be','been','being','have','has','had','do','does','did','will','would',
             'could','should','may','might','shall','i','we','you','they','he','she','it','this',
             'that','these','those','my','your','our','their','his','her','its'}

def _keywords(text, n=30):
    """Extract top N keywords from text using TF-IDF."""
    text = re.sub(r'[^a-zA-Z0-9\s+#]', ' ', text.lower())
    words = [w for w in text.split() if len(w) > 2 and w not in STOPWORDS]
    if not words:
        return []
    try:
        vec = TfidfVectorizer(ngram_range=(1, 2), max_features=200)
        vec.fit([' '.join(words)])
        scores = dict(zip(vec.get_feature_names_out(), vec.idf_))
        return sorted(scores, key=scores.get)[:n]
    except Exception:
        return list(set(words))[:n]

def _similarity(text1, text2):
    """Cosine similarity between two texts."""
    try:
        vec = TfidfVectorizer()
        tfidf = vec.fit_transform([text1, text2])
        return float(cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0])
    except Exception:
        return 0.0

def analyze(resume_text):
    """Resume analysis using TF-IDF keyword extraction and rule-based scoring."""
    text = resume_text.lower()
    words = resume_text.split()
    word_count = len(words)

    # Section detection
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

    # Scoring
    s_score = sum(sections.values()) / len(sections) * 100
    exp_score = 70 if sections['experience'] else 30
    edu_score = 80 if sections['education'] else 40
    skill_score = 85 if sections['skills'] else 35
    fmt_score = 60 + (10 if has_email else 0) + (10 if has_phone else 0) + (10 if 250 <= word_count <= 1200 else 0) + (10 if sections['projects'] else 0)
    grammar_score = 75  # static estimate
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

def ats_semantic(resume_text):
    """Semantic ATS evaluation using TF-IDF keyword density."""
    text = resume_text.lower()
    keywords = _keywords(resume_text, 15)
    ats_keywords = ['python','java','javascript','sql','management','leadership','communication',
                    'teamwork','agile','scrum','machine learning','data','analysis','development',
                    'design','testing','documentation','problem solving','bachelor','master']
    found_kw = [k for k in ats_keywords if k in text]
    score = min(100, 50 + len(found_kw) * 3)
    semantic_issues = []
    if len(found_kw) < 5: semantic_issues.append('Low keyword density for ATS scanners.')
    if not re.search(r'summary|objective', text): semantic_issues.append('Missing career summary or objective statement.')
    return {
        'score': score,
        'semantic_issues': semantic_issues,
        'keyword_suggestions': [k for k in ats_keywords if k not in text][:8],
        'recommendations': ['Use industry-standard keywords from job postings.',
                            'Keep formatting simple — avoid tables and complex layouts.',
                            'Use standard section headings (Experience, Education, Skills).'],
    }

def match_job(resume_text, job_text):
    """Match resume to job description using TF-IDF cosine similarity."""
    sim = _similarity(resume_text, job_text)
    match_percent = int(sim * 100)

    resume_kw = set(_keywords(resume_text, 40))
    job_kw = set(_keywords(job_text, 40))

    matching = list(resume_kw & job_kw)
    missing = list(job_kw - resume_kw)
    required = list(job_kw)[:20]

    return {
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

def improve(resume_text, section, original_text, facts):
    """Provide improvement suggestions for a resume section."""
    text = original_text or resume_text
    keywords = _keywords(text, 10)
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
        'original': original_text or f'[{section} section from your resume]',
        'improved': (original_text or '') + '\n\n[Rewrite tip: ' + suggestions[0] + ']',
        'changes': suggestions,
        'action_verbs': action_verbs,
        'recommended_skills': keywords[:8],
        'notes': f'Focus on improving your {section} by using the suggestions above. scikit-learn keyword analysis found: {", ".join(keywords[:5])}',
    }
