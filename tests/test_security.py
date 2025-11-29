import unittest
from flask import current_app
from main import app, db
from models import User, Role


class SecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = app
        cls.client = cls.app.test_client()
        cls.app_context = cls.app.app_context()
        cls.app_context.push()

    @classmethod
    def tearDownClass(cls):
        cls.app_context.pop()

    def setUp(self):
        db.session.rollback()

    def test_sql_injection_login(self):
        payload_email = "' OR '1'='1"
        payload_password = "anything"
        resp = self.client.post('/login', data={'email': payload_email, 'password': payload_password}, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Неверный email или пароль', resp.get_data(as_text=True))

    def test_xss_escape_in_management(self):
        admin_role = Role.query.filter_by(name='Admin').first()
        user_role = Role.query.filter_by(name='User').first()

        # Ensure admin exists and login
        admin_user = User.query.join(Role).filter(Role.name == 'Admin').first()
        self.assertIsNotNone(admin_user)
        self.client.post('/login', data={'email': admin_user.email, 'password': 'Admin31082003'}, follow_redirects=True)

        # Create a user with XSS-like username
        malicious_username = '<script>alert(1)</script>'
        u = User(username='xss_user', email='xss@example.com', password_hash=admin_user.password_hash,
                 role_id=user_role.id, is_active=True, first_name=malicious_username)
        db.session.add(u)
        db.session.commit()

        resp = self.client.get('/admin/adminmanagementview/', follow_redirects=True)
        text = resp.get_data(as_text=True)
        # Jinja2 autoescape should escape tags
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', text)

        # cleanup
        db.session.delete(u)
        db.session.commit()

    def test_registration_form_validation(self):
        # Invalid email should fail form validation (Flask-WTF)
        from forms import RegistrationForm
        with self.app.test_request_context('/register', method='POST', data={
            'first_name': 'Test',
            'last_name': 'User',
            'middle_name': '',
            'email': 'invalid-email',
            'password': 'secret123',
            'confirm_password': 'secret123'
        }):
            form = RegistrationForm()
            self.assertFalse(form.validate())


if __name__ == '__main__':
    unittest.main()