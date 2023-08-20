# from model import *
from helpers import *


def test_all():
    test_user()
    test_image()
    test_board()


def test_user():
    """Creates test user in test database"""
    register_user('Guppy', 'guppy@thecat.com', 'badpw')


def test_image():
    """Creates test image in test database"""
    upload_image(
        "https://s.keepmeme.com/files/en_posts/20200822/cc83fa3c7f8f8d04b3cdb12d65d57101confused-cat-with-a-lot-of"
        "-question-marks.jpg",
        'this cat is CONFUSE',
        1,
        False,
        None
    )


def test_board():
    """Creates test board in test database"""

    tester_board = Board(
        name='honey badgers',
        icon='fas fa-badger-honey',
        hex_code='#FFC0CB',
        user_id=1)
    db.session.add(tester_board)
    db.session.commit()
