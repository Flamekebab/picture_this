from werkzeug.datastructures import FileStorage
import shutil
import unittest
import os

import helpers

os.environ['PT_TESTING_MODE'] = 'True'
os.system('export PT_TESTING_MODE')
from server import app
from model import db
from helpers import *


# TODO sharing tests
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
        self.assertIn(b"/upload</a>", result.data)
        self.assertNotIn(b"log in</a> to access this page", result.data)

    def test_3_create_duplicate_board(self):
        """Does the app refuse to create a duplicate board?"""
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
        self.assertNotIn(b"log in</a> to access this page", result.data)
        self.assertEqual(result.status_code, 302)
        with self.client.session_transaction() as session:
            # A list of tuples - e.g. [('message', 'A board called honey badgers already exists')]
            flash_messages = session['_flashes']
        self.assertEqual(flash_messages[0][1], "A board called honey badgers already exists")

    def test_4_upload_from_url(self):
        """Can we upload an image from a URL?"""
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['username'] = 'Guppy'

        form_data = {
            "board_id": 1,
            "file-or-url": "url",
            "url": "https://upload.wikimedia.org/wikipedia/commons/9/92/Manul1a.jpg",
            "notes": "Testing uploads through the medium of pallas cats",
            "private": False
        }
        result = self.client.post("/api/upload", data=form_data)
        self.assertIn(b"/board/Guppy/honey badgers", result.data)

    def test_5_my_images_logged_in(self):
        """Does the My Images page load when logged in?"""
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['username'] = 'Guppy'

        result = self.client.get("/my_images")
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"pallas cats", result.data)

    def test_6_upload_from_file(self):
        """Can we upload from a file?"""
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['username'] = 'Guppy'

        # We have a file to hand (the first image we uploaded) - we can upload it as a file!
        file_path = "./test_uploads/1.webp"
        with open(file_path, "rb") as file:
            # Create a Werkzeug FileStorage object from the file
            file_storage = FileStorage(file)
            form_data = {
                "board_id": 1,
                "file-or-url": "file",
                "url": "",
                "notes": "How about the same picture again?",
                "private": False,
                "attached-file": file_storage
            }
            result = self.client.post("/api/upload", data=form_data)
        self.assertIn(b"/board/Guppy/honey badgers", result.data)

    def test_7_delete_image(self):
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

    def test_8_delete_board(self):
        """Can we delete a board?"""
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['username'] = 'Guppy'

        result = self.client.get("/delete_board/Guppy/honey badgers")
        self.assertEqual(result.status_code, 302)
        with self.client.session_transaction() as session:
            # A list of tuples - e.g. [('message', 'honey badgers deleted!')]
            flash_messages = session['_flashes']
        self.assertEqual(flash_messages[0][1], "honey badgers deleted!")

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


class HelperTests(unittest.TestCase):
    """Tests for helper functions."""

    @classmethod
    def setUpClass(cls):
        # Create the database
        db.create_all()
        # Create the temporary upload directories
        os.makedirs(os.path.dirname("./test_uploads/thumbnails/"), exist_ok=True)

        helpers.register_user("Guppy", "guppy@thecat.com", "badpw")
        helpers.create_board("honey badgers", "fas fa-badger-honey", "#FFC0CB", 1)

    def setUp(self):
        """Code to run before every test."""
        self.client = app.test_client()  # test_client from Werkzeug library returns a "browser" to "run" app

    def test_1_get_all_users_1(self):
        user_list = helpers.get_all_users()
        self.assertEqual(len(user_list), 1)
        self.assertEqual(user_list[0].username, "Guppy")

    def test_1_get_all_users_2(self):
        # Create another user, partly because later tests need multiple users
        helpers.register_user("Loja", "loja@thecat.com", "vbadpw")

        user_list = helpers.get_all_users()
        self.assertEqual(len(user_list), 2)
        self.assertEqual(user_list[1].email, "loja@thecat.com")

    def test_1_upload_image_invalid_type(self):
        self.assertFalse(helpers.upload_image("https://pt.test/invalid.image", "", 1, 1))

    def test_1_upload_image_invalid_url(self):
        self.assertFalse(helpers.upload_image("https://upload.wikimedia.org/Manul1a.jpg", "", 1, 1))

    def test_1_upload_image_valid_url(self):
        self.assertTrue(helpers.upload_image("https://upload.wikimedia.org/wikipedia/commons/9/92/Manul1a.jpg",
                                             "Testing uploads through the medium of pallas cats",
                                             1,
                                             1))

    def test_1_get_user_id_by_username(self):
        user_id = helpers.get_user_id_by_username("Guppy")
        self.assertEqual(user_id, 1)

    def test_1_get_board_from_id(self):
        board = helpers.get_board_from_id(1)
        self.assertEqual(board.name, "honey badgers")

    def test_1_get_board_id_by_board_name(self):
        self.assertEqual(helpers.get_board_id_by_board_name("honey badgers", 1), 1)

    def test_2_board_thumbnail_set_valid(self):
        self.assertTrue(helpers.board_thumbnail_set(1, 1))

    def test_2_get_shareable_users(self):
        user_list = helpers.get_shareable_users(1, 1)
        self.assertEqual(user_list[0]['username'], "Loja")
        self.assertEqual(user_list[0]['user_id'], 2)

    def test_2_get_images_by_user(self):
        self.assertEqual(len(helpers.get_images_by_user(1)), 1)

    # This test has to happen after other boards and images exist
    # def test_3_board_thumbnail_set_invalid(self):
    #     self.assertFalse(helpers.board_thumbnail_set(1, 2))

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
