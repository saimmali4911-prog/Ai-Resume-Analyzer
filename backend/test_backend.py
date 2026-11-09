import io
import json
import unittest
from app import app, db
from models import User, Profile, Resume

class BackendTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        cls.client = app.test_client()

    def setUp(self):
        with app.app_context():
            db.drop_all()
            db.create_all()

    def test_full_workflow(self):
        c = self.client

        # 1. Health check
        res = c.get('/api/health')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()['status'], 'ok')
        print("✓ Health check passed")

        # 2. Register user
        reg_payload = {
            'username': 'testdev2026',
            'email': 'testdev2026@example.com',
            'password': 'password123',
            'first_name': 'Test',
            'last_name': 'Developer'
        }
        res = c.post('/api/auth/register', json=reg_payload)
        self.assertIn(res.status_code, (200, 201))
        reg_data = res.get_json()
        token = reg_data['token']
        self.assertTrue(token)
        headers = {'Authorization': f'Bearer {token}'}
        print("✓ User registration passed")

        # 3. Me endpoint
        res = c.get('/api/auth/me', headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()['user']['username'], 'testdev2026')
        print("✓ GET /api/auth/me passed")

        # 4. Profile update
        prof_payload = {
            'target_role': 'Full Stack Engineer',
            'phone': '+1234567890',
            'bio': 'Passionate about decoupled architectures.'
        }
        res = c.put('/api/auth/profile', json=prof_payload, headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()['user']['profile']['target_role'], 'Full Stack Engineer')
        print("✓ PUT /api/auth/profile passed")

        # 5. Upload resume (mock a PDF with %PDF header)
        sample_resume_text = (
            "Professional Summary\n"
            "Experienced Python Full Stack Developer with 5 years building scalable web applications.\n\n"
            "Work Experience\n"
            "Senior Software Engineer at Acme Corp (2021-2026)\n"
            "- Designed RESTful APIs using Flask and Python.\n"
            "- Built interactive dashboards with JavaScript and Chart.js.\n"
            "- Managed SQL databases and optimized queries by 30%.\n\n"
            "Education\n"
            "Bachelor of Science in Computer Science, University of Technology\n\n"
            "Technical Skills\n"
            "Python, Flask, JavaScript, SQL, Docker, Git, REST APIs, HTML, CSS\n\n"
            "Contact: testdev2026@example.com | +1234567890 | linkedin.com/in/testdev"
        )
        # Create a valid minimal PDF in-memory using pymupdf
        import pymupdf
        pdf_doc = pymupdf.open()
        page = pdf_doc.new_page()
        page.insert_text((50, 72), sample_resume_text)
        pdf_bytes = pdf_doc.tobytes()
        pdf_doc.close()

        data = {
            'title': 'Test Senior Developer Resume',
            'file': (io.BytesIO(pdf_bytes), 'resume.pdf')
        }
        res = c.post('/api/resumes/upload', data=data, content_type='multipart/form-data', headers=headers)
        self.assertEqual(res.status_code, 201)
        res_data = res.get_json()
        resume_id = res_data['resume']['id']
        self.assertTrue(resume_id)
        print(f"✓ POST /api/resumes/upload passed (Resume ID: {resume_id})")

        # 6. List resumes
        res = c.get('/api/resumes', headers=headers)
        self.assertEqual(res.status_code, 200)
        res_list = res.get_json()
        self.assertGreaterEqual(len(res_list), 1)
        print("✓ GET /api/resumes passed")

        # 7. Get resume text
        res = c.get(f'/api/resumes/{resume_id}/text', headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertIn('Python', res.get_json()['text'])
        print("✓ GET /api/resumes/<id>/text passed")

        # 8. Download resume file
        res = c.get(f'/api/resumes/{resume_id}/file', headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data.startswith(b'%PDF'))
        res.close()
        print("✓ GET /api/resumes/<id>/file passed")

        # 9. Run Analysis (Score)
        res = c.post('/api/analysis/run/analysis', json={'resume_id': resume_id}, headers=headers)
        self.assertEqual(res.status_code, 200)
        an_data = res.get_json()
        an_id = an_data['id']
        self.assertGreater(an_data['score'], 0)
        print(f"✓ Analysis Tool passed (Score: {an_data['score']})")

        # 10. Run ATS Checker
        res = c.post('/api/analysis/run/ats', json={'resume_id': resume_id}, headers=headers)
        self.assertEqual(res.status_code, 200)
        ats_data = res.get_json()
        ats_id = ats_data['id']
        self.assertGreater(ats_data['score'], 0)
        print(f"✓ ATS Checker Tool passed (Score: {ats_data['score']})")

        # 11. Run Job Match
        job_desc = (
            "Looking for a Senior Python Developer with extensive experience in Flask, "
            "REST APIs, SQL databases, Docker, and frontend JavaScript. "
            "Requires bachelor degree in Computer Science or related field."
        )
        res = c.post('/api/analysis/run/match', json={
            'resume_id': resume_id,
            'job_title': 'Lead Python Engineer',
            'job_description': job_desc
        }, headers=headers)
        self.assertEqual(res.status_code, 200)
        match_data = res.get_json()
        match_id = match_data['id']
        self.assertGreaterEqual(match_data['score'], 0)
        print(f"✓ Job Matching Tool passed (Match: {match_data['score']}%)")

        # 12. Run Improvement
        res = c.post('/api/analysis/run/improve', json={
            'resume_id': resume_id,
            'section': 'Work Experience',
            'original': 'Developed web applications and worked on APIs.',
            'facts': 'Handled 50k daily active users and improved response times by 40%.'
        }, headers=headers)
        self.assertEqual(res.status_code, 200)
        imp_data = res.get_json()
        imp_id = imp_data['id']
        self.assertTrue(imp_data['data']['improved'])
        print("✓ Improvement Tool passed")

        # 13. Analysis History
        res = c.get('/api/analysis/history', headers=headers)
        self.assertEqual(res.status_code, 200)
        history = res.get_json()
        self.assertGreaterEqual(len(history), 4)
        print(f"✓ GET /api/analysis/history passed ({len(history)} items)")

        # 14. Specific Analysis by Kind & ID
        res = c.get(f'/api/analysis/analysis/{an_id}', headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()['kind'], 'analysis')
        print("✓ GET /api/analysis/<kind>/<id> passed")

        # 15. Dashboard Stats
        res = c.get('/api/dashboard', headers=headers)
        self.assertEqual(res.status_code, 200)
        dash = res.get_json()
        self.assertEqual(dash['n_resumes'], 1)
        self.assertGreaterEqual(dash['n_analyses'], 4)
        self.assertEqual(len(dash['chart']['an']), 1)
        print("✓ GET /api/dashboard passed")

        # 16. Delete Resume
        res = c.delete(f'/api/resumes/{resume_id}', headers=headers)
        self.assertEqual(res.status_code, 200)
        print("✓ DELETE /api/resumes/<id> passed")

        # Verify resume list is now empty
        res = c.get('/api/resumes', headers=headers)
        self.assertEqual(len(res.get_json()), 0)
        print("✓ Resume deletion confirmed")

        # 17. Logout
        res = c.post('/api/auth/logout', headers=headers)
        self.assertEqual(res.status_code, 200)
        print("✓ POST /api/auth/logout passed")

if __name__ == '__main__':
    unittest.main()
