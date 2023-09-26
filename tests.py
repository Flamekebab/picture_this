import os
os.environ['PT_TESTING_MODE'] = 'True'
os.system('export PT_TESTING_MODE')
from server import app
from model import db
import unittest
import test_seed_data


class ServerTests(unittest.TestCase):
    """Tests for Picture This app."""

    def setUp(self):
        """Code to run before every test."""
        self.client = app.test_client()  # test_client from Werkzeug library returns a "browser" to "run" app
        db.create_all()
        test_seed_data.test_all()
        # ** see test_seed_data.py for test_data helper functions ** #

    def test_homepage(self):
        """Does homepage load?"""

        result = self.client.get("/")
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Log Your Bad Self In", result.data)

    def test_my_images_logged_out(self):
        """Does the My Images page load without login?"""

        result = self.client.get("/my_images")
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Log Your Bad Self In", result.data)

    def test_my_images_logged_in(self):
        """Does the My Images page load when logged in?"""
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['username'] = 'Guppy'
        result = self.client.get("/my_images")
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"this cat is CONFUSE", result.data)

    # TODO - write more logged in tests

    def test_upload_page(self):
        """Does Upload page load?"""

        result = self.client.get("/upload")
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"to access this page", result.data)

    def tearDown(self):
        """Code to run after every test"""

        db.session.remove()
        db.drop_all()
        db.engine.dispose()


if __name__ == "__main__":
    unittest.main(verbosity=2)
