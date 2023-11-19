from unittest.mock import patch

from werkzeug.datastructures import FileStorage
import unittest
import os

import helpers

os.environ['PT_TESTING_MODE'] = 'True'
os.system('export PT_TESTING_MODE')
from server import app
from helpers import *
from model import *


class ModelTests(unittest.TestCase):
    """Mainly so the coverage report looks pretty, to be honest"""

    test_user = User(
        user_id=1,
        username="Guppy",
        email="guppy@thecat.com",
        password_hashed=User.get_hash("badpw"))
    test_board = Board(
        board_id=1,
        name="honey badgers",
        icon="fas fa-badger-honey",
        hex_code="#FFC0CB",
        user_id=1)
    test_image = Image(
        image_id=1,
        thumbnail=1,
        url="https://upload.wikimedia.org/wikipedia/commons/9/92/Manul1a.jpg",
        file_extension=".webp",
        notes="Testing uploads through the medium of pallas cats",
        private=False,
        user_id=1,
        board_id=1,
    )

    def test_user_repr(self):
        """Does the User class' custom repr() work?"""
        user = "<User user_id=1, username=Guppy, email=guppy@thecat.com>"
        self.assertEqual(repr(self.test_user), user)

    def test_board_repr(self):
        """Does the Board class' custom repr() work?"""
        board = "<Board board_id=1, name=honey badgers>"
        self.assertEqual(repr(self.test_board), board)

    def test_image_repr(self):
        """Does the Image class' custom repr() work?"""
        image = "<Image image_id=1, url=https://upload.wikimedia.org/wikipedia/commons/9/92/Manul1a.jpg>"
        self.assertEqual(repr(self.test_image), image)


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

    def test_server_1_homepage(self):
        """Does homepage load at all?"""
        result = self.client.get("/")
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Log Your Bad Self In", result.data)

    def test_server_1_logged_out_my_images(self):
        """Does the My Images page load without login?"""
        result = self.client.get("/my_images")
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Log Your Bad Self In", result.data)

    def test_server_1_logged_out_upload_page(self):
        """Does Upload page load but actually redirect?"""
        result = self.client.get("/upload")
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Log Your Bad Self In", result.data)

    def test_server_1_upload_api_logged_out(self):
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

    def test_server_1_registration_page(self):
        """Does registration page load?"""
        result = self.client.get("/register")
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Register", result.data)

    def test_server_2_register(self):
        """Can we register a user?"""
        form_data = {
            "username": "Guppy",
            "email": "guppy@thecat.com",
            "password": "badpw",
        }
        result = self.client.post("/api/register_user", data=form_data)
        # Success renders the login page, failure redirects to registration page
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Log Your Bad Self In", result.data)

        # Repeat the process to try to coax failures
        form_data = {
            "username": "Guppy",
            "email": "guppy2@thecat.com",
            "password": "badpw",
        }
        result = self.client.post("/api/register_user", data=form_data)
        self.assertIn(b"/register</a>", result.data)

        form_data = {
            "username": "Guppy2",
            "email": "guppy@thecat.com",
            "password": "badpw",
        }
        result = self.client.post("/api/register_user", data=form_data)
        self.assertIn(b"/register</a>", result.data)

        # We need to register another user for the later tests so might as well do it here
        form_data = {
            "username": "Loja",
            "email": "loja@thecat.com",
            "password": "vbadpw",
        }
        result = self.client.post("/api/register_user", data=form_data)
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Log Your Bad Self In", result.data)

    def test_server_3_login(self):
        """Attempt various logins"""
        form_data = {
            "email": "guppy@thecat.com",
            "password": "wrong",
        }
        result = self.client.post("/api/log_in", data=form_data)
        self.assertIn(b"Incorrect password!", result.data)
        # Try logging in using an email address that doesn't exist
        form_data = {
            "email": "cricket@thedog.com",
            "password": "badpw",
        }
        result = self.client.post("/api/log_in", data=form_data)
        self.assertIn(b"Email doesn&#39;t exist in database!", result.data)
        # How about the correct details:
        form_data = {
            "email": "guppy@thecat.com",
            "password": "badpw",
        }
        result = self.client.post("/api/log_in", data=form_data)
        # The redirecting message mentions /my_images, the destination users go to after logging in
        self.assertIn(b">/my_images</a>", result.data)

        # If we're already logged in it should redirect
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['username'] = 'Guppy'

            result = self.client.get("/log_in")
            self.assertEqual(result.status_code, 200)
            self.assertIn(b"My Images", result.data)

    def test_server_3_create_board(self):
        """Can a registered user create a board?"""
        # First test that it refuses if not logged in
        result = self.client.post("/api/add_board")
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Log Your Bad Self In", result.data)

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

    def test_server_4_log_out(self):
        """Ensure logging out doesn't throw an error"""
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['username'] = 'Guppy'

        result = self.client.get("/api/log_out")
        self.assertEqual(result.status_code, 302)
        with self.client.session_transaction() as session:
            flash_messages = session['_flashes']
        self.assertEqual(flash_messages[0][1], "Logout successful.")

    def test_server_4_create_duplicate_board(self):
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

    def test_server_4_upload_from_url(self):
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

    def test_server_4_fail_to_upload(self):
        """Does it stop us from uploading?"""
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['username'] = 'Guppy'

        # Board 3 isn't one of the allowed boards
        form_data = {
            "board_id": 3,
            "file-or-url": "url",
            "url": "https://upload.wikimedia.org/wikipedia/commons/9/92/Manul1a.jpg",
            "notes": "Testing uploads through the medium of pallas cats",
            "private": False
        }
        result = self.client.post("/api/upload", data=form_data)
        self.assertEqual(result.status_code, 302)

        # This should only be possible through form manipulation:
        form_data = {
            "board_id": 1,
            "file-or-url": "url",
            "url": "",
            "notes": "Testing uploads through the medium of pallas cats",
            "private": False
        }
        result = self.client.post("/api/upload", data=form_data)
        self.assertEqual(result.status_code, 302)

        with self.client.session_transaction() as session:
            flash_messages = session['_flashes']
        self.assertIn("You do not have permission to upload to that board!", flash_messages[0][1])
        self.assertIn("Upload failed", flash_messages[1][1])

    def test_server_5_my_images_logged_in(self):
        """Does the My Images page load when logged in?"""
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['username'] = 'Guppy'

        result = self.client.get("/my_images")
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"pallas cats", result.data)

    def test_server_5_serve_image_file(self):
        result = self.client.get("/uploads/1.webp")
        self.assertEqual(result.status_code, 200)

    def test_server_6_upload_from_file(self):
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

        # Test that it fails when supplied with an unsuitable file
        file_path = "./demo_data.py"
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
        self.assertEqual(result.status_code, 302)
        with self.client.session_transaction() as session:
            # A list of tuples - e.g. [('message', 'Image deleted successfully')]
            flash_messages = session['_flashes']
        self.assertIn("Upload failed", flash_messages[1][1])

    def test_server_6_share_board(self):
        """Do the correct share board options populate?"""
        # Logged out
        result = self.client.get("/share_board/Guppy/honey badgers")
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Log Your Bad Self In", result.data)

        # Logged in
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['username'] = 'Guppy'
        result = self.client.get("/share_board/Guppy/honey badgers")
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Share a Board", result.data)

    # TODO: Add other attempts to share that should fail
    def test_server_7_share_board_form(self):
        """Can we actually share boards, where appropriate?"""
        form_data = {
            "board_id": 1,
            "user_id": 2,
        }
        # Logged out
        result = self.client.post("/api/share_board", data=form_data)
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Log Your Bad Self In", result.data)

        # Logged in
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['username'] = 'Guppy'

        result = self.client.post("/api/share_board", data=form_data)
        self.assertEqual(result.status_code, 302)
        self.assertIn(b"boards</a>", result.data)
        with self.client.session_transaction() as session:
            flash_messages = session['_flashes']
        self.assertIn("Shared honey badgers with Loja", flash_messages[0][1])

    # TODO Uploading to shared boards
    # TODO Unshare board
    # def test_server_8_upload_page_with_shared_boards(self):
    #     """Does the upload page show shared boards?"""
    #     with self.client.session_transaction() as session:
    #         session['user_id'] = 1
    #         session['username'] = 'Guppy'
    #     result = self.client.get("/upload/Guppy/honey badgers")
    #     self.assertEqual(result.status_code, 200)
    #     self.assertIn(b"Add a photo", result.data)
    #
    #     with self.client.session_transaction() as session:
    #         session['user_id'] = 2
    #         session['username'] = 'Loja'
    #     result = self.client.get("/upload/Guppy/honey badgers")
    #     self.assertEqual(result.status_code, 200)
    #     # If the sharing code works properly Loja should now be able to upload to Guppy's board
    #     self.assertIn(b"honey badgers", result.data)



    def test_server_8_show_board(self):
        """Show one of the user's boards, where appropriate"""
        # This has to wait until after the board sharing tests

        # Logged out
        result = self.client.get("/board/Guppy/honey badgers")
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Log Your Bad Self In", result.data)

        # Logged in
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['username'] = 'Guppy'

        result = self.client.get("/board/Guppy/honey badgers")
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"honey badger", result.data)

    def test_server_8_show_boards(self):
        """Show the user's boards, where appropriate"""
        # This has to wait until after the board sharing tests

        # Logged out
        result = self.client.get("/boards")
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Log Your Bad Self In", result.data)

        # Logged in
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['username'] = 'Guppy'

        result = self.client.get("/boards")
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"My Boards", result.data)

    def test_server_9_1_delete_image(self):
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

        # Try to delete an image that we shouldn't be able to:
        result = self.client.get("/delete/3")
        # This will generate the second flash message ("Failed to delete image")
        self.assertEqual(result.status_code, 302)
        with self.client.session_transaction() as session:
            flash_messages = session['_flashes']
        self.assertEqual(flash_messages[2][1], "Failed to delete image")

    def test_server_9_2_delete_board(self):
        """Can we delete a board with the appropriate credentials?"""
        # Not logged in
        result = self.client.get("/delete_board/Guppy/honey badgers")
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Log Your Bad Self In", result.data)

        # Try to delete someone else's board
        with self.client.session_transaction() as session:
            session['user_id'] = 2
            session['username'] = 'Loja'
        result = self.client.get("/delete_board/Guppy/honey badgers")
        self.assertEqual(result.status_code, 302)

        # Log in as Guppy and test:
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['username'] = 'Guppy'
        # Try to delete a board that doesn't exist
        result = self.client.get("/delete_board/Guppy/invalid board")
        self.assertEqual(result.status_code, 302)

        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['username'] = 'Guppy'
        result = self.client.get("/delete_board/Guppy/honey badgers")
        self.assertEqual(result.status_code, 302)
        with self.client.session_transaction() as session:
            flash_messages = session['_flashes']

        self.assertEqual(flash_messages[0][1], "You do not have permission to delete Guppy's board!")
        self.assertEqual(flash_messages[1][1], "Problem encountered deleting invalid board!")
        self.assertEqual(flash_messages[2][1], "honey badgers deleted!")

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

    def test_1_helpers_check_email(self):
        """Pass in an email address that's not in the database"""
        self.assertRaises(TypeError, helpers.check_email("cricket@thedog.com"))

    def test_helpers_1_get_all_users_1(self):
        user_list = helpers.get_all_users()
        self.assertEqual(len(user_list), 1)
        self.assertEqual(user_list[0].username, "Guppy")

    def test_helpers_1_get_all_users_2(self):
        # Create another user, partly because later tests need multiple users
        helpers.register_user("Loja", "loja@thecat.com", "vbadpw")

        user_list = helpers.get_all_users()
        self.assertEqual(len(user_list), 2)
        self.assertEqual(user_list[1].email, "loja@thecat.com")

    def test_helpers_1_upload_image_invalid_type(self):
        self.assertFalse(helpers.upload_image("https://pt.test/invalid.image",
                                              "",
                                              1,
                                              1,
                                              upload_dir="test_uploads"))

    def test_helpers_1_upload_image_invalid_url(self):
        self.assertFalse(helpers.upload_image("https://upload.wikimedia.org/Manul1a.jpg",
                                              "",
                                              1,
                                              1,
                                              upload_dir="test_uploads"))

    def test_helpers_1_upload_image_file(self):
        class InputImage:
            def __init__(self, filename):
                self.filename = filename

            # When attempting to save this fake file object, raise an exception
            def save(self, path):
                raise Exception

        input_image = InputImage(
            filename="invalid.file")
        self.assertFalse(helpers.upload_image(input_image,
                                              "This file is the wrong type",
                                              1,
                                              1,
                                              file_or_url="file",
                                              upload_dir="test_uploads")
                         )

        input_image = InputImage(
            filename="valid.jpg")
        self.assertFalse(helpers.upload_image(input_image,
                                              "This file doesn't save",
                                              1,
                                              1,
                                              file_or_url="file",
                                              upload_dir="test_uploads"
                                              )
                         )

    @patch('os.path.getsize')
    def test_helpers_1_webp_if_larger(self, mock_getsize):
        """What if the JPG is smaller than the WebP?"""
        mock_getsize.return_value = 1000
        self.assertFalse(helpers.webp_if_larger("./static/img/journaly.jpg"))

    def test_helpers_1_upload_image_valid_url(self):
        self.assertTrue(helpers.upload_image("https://upload.wikimedia.org/wikipedia/commons/9/92/Manul1a.jpg",
                                             "Testing uploads through the medium of pallas cats",
                                             1,
                                             1,
                                             upload_dir="test_uploads")
                        )

    def test_helpers_1_get_user_id_by_username(self):
        user_id = helpers.get_user_id_by_username("Guppy")
        self.assertEqual(user_id, 1)

    def test_helpers_1_get_board_from_id(self):
        board = helpers.get_board_from_id(1)
        self.assertEqual(board.name, "honey badgers")

    def test_helpers_1_get_board_id_by_board_name(self):
        self.assertEqual(helpers.get_board_id_by_board_name("honey badgers", 1), 1)

    def test_helpers_1_delete_image_unsuccessfully(self):
        self.assertFalse(helpers.delete_image(1, 3))

    def test_helpers_1_delete_board_unsuccessfully(self):
        self.assertFalse(helpers.delete_board(1, "not a board"))

    def test_helpers_2_board_images_for_user_found(self):
        self.assertEqual(len(helpers.board_images_for_user(1, "honey badgers")), 1)

    def test_helpers_2_board_thumbnail_set_valid(self):
        self.assertTrue(helpers.board_thumbnail_set(1, 1))

    def test_helpers_2_get_shareable_users(self):
        user_list = helpers.get_shareable_users(1, 1)
        self.assertEqual(user_list[0]['username'], "Loja")
        self.assertEqual(user_list[0]['user_id'], 2)

    def test_helpers_2_get_images_by_user(self):
        self.assertEqual(len(helpers.get_images_by_user(1)), 1)
        self.assertEqual(len(helpers.board_images_for_user(2, "honey badgers")), 0)

    def test_helpers_3_board_thumbnail_set_invalid(self):
        helpers.create_board("Loja's board", "fas fa-badger-honey", "#FFC0CB", 2)
        helpers.upload_image("https://upload.wikimedia.org/wikipedia/commons/9/92/Manul1a.jpg",
                             "Same image but different board and user",
                             2,
                             2,
                             upload_dir="test_uploads")
        self.assertFalse(helpers.board_thumbnail_set(1, 2))

    def test_helpers_3_get_board_ids_shared_with_user_empty(self):
        self.assertCountEqual(helpers.get_board_ids_shared_with_user(1), [])

    def test_helpers_4_share_board_with_user(self):
        # The user that owns the board isn't a valid target to share with
        self.assertFalse(helpers.share_board_with_user(1, 1, 1))
        # The user that doesn't own the board can't request the board be shared with them
        self.assertFalse(helpers.share_board_with_user(1, 2, 2))
        # The owner (1) can share it with a viable target (2)
        self.assertTrue(helpers.share_board_with_user(1, 1, 2))

    def test_helpers_5_get_board_ids_shared_with_user(self):
        self.assertCountEqual(helpers.get_board_ids_shared_with_user(2), [1])

    def test_helpers_5_get_shared_with(self):
        self.assertEqual(helpers.get_shared_with(1, 1), ["Loja"])

    def test_helpers_5_board_images_for_shared_user(self):
        # The board isn't shared with the owner so this shouldn't provide images:
        self.assertFalse(helpers.board_images_for_shared_user(1, 1))
        # ...and a simple check for expected results
        self.assertEqual(len(helpers.board_images_for_shared_user(2, 1)), 1)

    def test_helpers_6_unshare_board_with_user(self):
        # Can't unshare your own board from yourself!
        self.assertFalse(helpers.unshare_board_with_user(1, 1))

    def test_helpers_7_unshare_board_with_user(self):
        # Combining this with the above test raises an sqlalchemy.orm.exc.StaleDataError for some reason
        self.assertTrue(helpers.unshare_board_with_user(1, 2))

    def test_helpers_8_delete_board(self):
        self.assertTrue(helpers.delete_board(1, "honey badgers", upload_dir="test_uploads"))

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
