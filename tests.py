import os
import shutil
import unittest
os.environ['PT_TESTING_MODE'] = 'True'
os.system('export PT_TESTING_MODE')
from server import app
from model import db


class ServerTests(unittest.TestCase):
    """Tests for Picture This app."""

    @classmethod
    def setUpClass(cls):
        # Create the database
        db.create_all()
        # Create the temporary upload directories
        os.makedirs(os.path.dirname("./test_uploads/thumbnails/"), exist_ok=True)

    def setUp(self):
        """Code to run before every test."""
        self.client = app.test_client()  # test_client from Werkzeug library returns a "browser" to "run" app

    def test_1_homepage(self):
        """Does homepage load at all?"""
        result = self.client.get("/")
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Log Your Bad Self In", result.data)

    def test_1_logged_out_my_images(self):
        """Does the My Images page load without login?"""
        result = self.client.get("/my_images")
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Log Your Bad Self In", result.data)

    def test_1_logged_out_upload_page(self):
        """Does Upload page load but actually redirect?"""
        result = self.client.get("/upload")
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Log Your Bad Self In", result.data)

    def test_1_upload_api_logged_out(self):
        """Does uploading without being logged in fail as it should?"""
        # (I've swapped the URL for one I expect to be reliable for years to come)
        form_data = {
            "board_id": 1,
            "url": "https://upload.wikimedia.org/wikipedia/commons/9/92/Manul1a.jpg",
            "notes": "Testing uploads through the medium of pallas cats",
            "private": False
        }
        result = self.client.post("/api/upload", data=form_data)
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Log Your Bad Self In", result.data)

    def test_2_register(self):
        """Can we register a user?"""
        form_data = {
            "username": "Guppy",
            "email": "guppy@thecat.com",
            "password": "badpw",
        }
        result = self.client.post("/api/register_user", data=form_data)
        # Success renders the login page, failure redirects to root
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Log Your Bad Self In", result.data)

    def test_3_create_board(self):
        """Can a registered user create a board?"""
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['username'] = 'Guppy'

        form_data = {
            "name": "honey badgers",
            "icon": 'fas fa-badger-honey',
            "hex_code": '#FFC0CB',
            "user_id": 1
        }
        result = self.client.post("/api/add_board", data=form_data)
        self.assertIn(b"Add a photo", result.data)
        self.assertNotIn(b"log in</a> to access this page", result.data)

    def test_4_upload_from_url(self):
        """Can we upload an image from a URL?"""
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['username'] = 'Guppy'

        form_data = {
            "board_id": 1,
            "url": "https://upload.wikimedia.org/wikipedia/commons/9/92/Manul1a.jpg",
            "notes": "Testing uploads through the medium of pallas cats",
            "private": False
        }
        result = self.client.post("/api/upload", data=form_data)
        self.assertIn(b'You should be redirected automatically to target URL: <a href="/my_images">', result.data)

    def test_5_my_images_logged_in(self):
        """Does the My Images page load when logged in?"""
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['username'] = 'Guppy'

        result = self.client.get("/my_images")
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"pallas cats", result.data)

    def test_6_delete_image(self):
        """Can we delete images with the appropriate credentials?"""
        # First without being logged in:
        self.client.get("/delete/1")
        # This will generate the first flash message ("Login to delete images")

        # Log in and test:
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['username'] = 'Guppy'

        result = self.client.get("/delete/1")
        # This will generate the second flash message ("Image deleted successfully")
        self.assertEqual(result.status_code, 302)
        with self.client.session_transaction() as session:
            # A list of tuples - e.g. [('message', 'Image deleted successfully')]
            flash_messages = session['_flashes']

        self.assertEqual(flash_messages[0][1], "Login to delete images")
        self.assertEqual(flash_messages[1][1], "Image deleted successfully")

    # TODO: Add a unit test for uploading a file

    def tearDown(self):
        """Code to run after every test"""
        db.session.remove()

    @classmethod
    def tearDownClass(cls):
        # Delete the database
        db.drop_all()
        db.engine.dispose()
        # Delete the files we uploaded
        shutil.rmtree("./test_uploads/")


if __name__ == "__main__":
    unittest.main(verbosity=2)
