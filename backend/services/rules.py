"""Rule-based ATS checks (formatting / structure)."""
import re
HEAD = {'Summary': r'summary|objective|profile', 'Experience': r'experience|employment|work history',
        'Education': r'education|academic', 'Skills': r'skills|technologies|competenc',
        'Projects': r'projects', 'Certifications': r'certif'}
CORE = ['Summary', 'Experience', 'Education', 'Skills']

def ats_rules(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    heads = [l.lower() for l in lines if len(l) < 40]
    found = {k: any(re.search(p, h) for h in heads) for k, p in HEAD.items()}
    missing = [k for k in CORE if not found[k]]
    words = len(text.split())
    email = bool(re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', text))
    phone = bool(re.search(r'(\+?\d[\d\s().-]{8,}\d)', text))
    tabley = sum(1 for l in lines if '|' in l or '\t' in l or re.search(r'\S {3,}\S', l))
    ratio = tabley / max(len(lines), 1)
    bullets = sum(1 for l in lines if l[0] in '\u2022-*\u25aa\u25cf\u25e6\u2013')
    alpha = sum(c.isalpha() for c in text) / max(len(text), 1)
    odd = sum(1 for c in text if ord(c) > 0xF000 or c == '\ufffd')

    h_pts = round(30 * (4 - len(missing)) / 4)
    c_pts = 8 * email + 7 * phone
    l_pts = 15 if 250 <= words <= 1200 else 8 if 120 <= words <= 1800 else 3
    t_pts = 15 if ratio < .05 else 8 if ratio < .15 else 2
    b_pts = 10 if bullets >= 3 else 3
    e_pts = 15 if alpha > .6 and odd < 5 else 7 if alpha > .45 else 2
    checks = [
        dict(name='Standard section headings', ok=not missing, detail='Missing: ' + ', '.join(missing) if missing else 'Summary, Experience, Education and Skills found.'),
        dict(name='Contact information', ok=email and phone, detail=f"Email {'found' if email else 'NOT found'}; phone {'found' if phone else 'NOT found'}."),
        dict(name='Length / readability', ok=l_pts >= 15, detail=f'{words} words (ideal 250-1200).'),
        dict(name='Tables & columns', ok=t_pts == 15, detail=f'{tabley} table/column-like lines detected.' if tabley else 'No table/column patterns detected.'),
        dict(name='Bullet-point structure', ok=b_pts == 10, detail=f'{bullets} bullet lines found.'),
        dict(name='Text extraction quality', ok=e_pts == 15, detail=f'{round(alpha*100)}% readable characters, {odd} odd symbols.'),
    ]
    return dict(score=h_pts + c_pts + l_pts + t_pts + b_pts + e_pts, checks=checks, missing=missing,
                found=[k for k, v in found.items() if v])
