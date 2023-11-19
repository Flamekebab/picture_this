import os
import shutil
from pathlib import Path
import urllib.request
from urllib.parse import urlparse
from urllib.error import HTTPError

import sqlalchemy.exc
from PIL import Image as PillowImage
from werkzeug.utils import secure_filename
import logging
from model import db, User, Image, Board

logging.basicConfig(level=logging.INFO)


# * General queries * #

def get_all_users():
    return User.query.all()


def get_user_by_user_id(user_id):
    return User.query.filter(User.user_id == user_id).first()


def get_user_id_by_username(username):
    return User.query.filter(User.username == username).first().user_id


def get_board_from_id(board_id):
    """
    Get the board object using its ID
    :param (int) board_id:
    :return: board SQLAlchemy object
    """
    return Board.query.get(board_id)


def get_board_name_by_board_id(board_id):
    return Board.query.filter(Board.board_id == board_id).first().name


def get_board_id_by_board_name(board_name, user_id):
    """
    Board names aren't unique but they are per-user.
    :param (str) board_name:
    :param (int) user_id:
    :return: (int) the id of the board requested
    """
    return Board.query.filter(Board.name == board_name, Board.user_id == user_id).first().board_id


def get_board_owner(board_id):
    """
    Find out which user owns this board
    :param (int) board_id: board_id
    :return: User object
    """
    return Board.query.get(board_id).user


# Sharing boards
def get_shared_with(board_id, user_id):
    """
    Get the usernames this board is shared with, excluding the owner of the board
    :param (int) board_id: requested board
    :param (int) user_id: owner of the board
    :return: (list) a list of usernames
    """
    # Get queries based on the primary key, unlike a filter
    board = Board.query.get(board_id)
    owner = User.query.get(user_id)
    shared_with = []
    for user in board.shared_with:
        if user.user_id != owner.user_id:
            shared_with.append(user.username)
    return shared_with


def get_user_board_ids(user_id):
    """
    Provides a list of board_ids that a user owns
    :param user_id: (int) User to search for boards for
    :return: (list) board_id values
    """
    boards = Board.query.filter(Board.user_id == user_id)
    board_ids = []
    for board in boards:
        board_ids.append(board.board_id)
    return board_ids


def get_board_ids_shared_with_user(user_id):
    """
    Get a list of board_ids that the user has shared with them (excluding ones they themselves own)
    :param (int) user_id: target user
    :return: (list) board_id values
    """
    all_shared_boards = []
    # We can ignore boards that the user already owns
    for board in Board.query.filter(Board.user_id != user_id).all():
        for user in board.shared_with:
            if user.user_id == user_id:
                all_shared_boards.append(board.board_id)
    return all_shared_boards


def share_board_with_user(board_id, owner_user_id, target_user_id):
    """
    Add a user to a board's share_with list, assuming they can be added
    :param (int) board_id: board to be shared with a user.
    :param (int) owner_user_id: user that owns this board
    :param (int) target_user_id: user to share the board with
    :return:
    """
    # Check that the user_id can be shared with that board
    available_target_users = get_shareable_users(owner_user_id, board_id)

    target_user = None
    for user in available_target_users:
        if user['user_id'] == target_user_id:
            target_user = get_user_by_user_id(user['user_id'])
            break

    # That user isn't one of the available options, do nothing
    if not target_user:
        return False

    # At this stage we can assume it's safe to make the requested changes
    board = Board.query.get(board_id)
    board.shared_with.append(target_user)
    db.session.commit()
    return True


def unshare_board_with_user(board_id, target_user_id):
    """
    Remove a user from a board's shared_with list
    :param board_id: (int) board to remove a guest from
    :param target_user_id: user_id for the guest
    :return:
    """
    board = Board.query.get(board_id)
    target_user = User.query.get(target_user_id)
    try:
        board.shared_with.remove(target_user)
        db.session.commit()
        return True
    except ValueError:
        return False


# * User registration & login * #

def check_username(username):
    """Check whether given username exists in users table."""
    return User.query.filter(User.username == username).first()


def check_email(email):
    """Check whether given email exists in users table."""
    try:
        user = User.query.filter(User.email == email).first()
    except sqlalchemy.exc.OperationalError:
        user = None

    return user


def register_user(username, email, password):
    """Add a user to the database."""
    user = User(
        username=username,
        email=email,
        password_hashed=User.get_hash(password))
    db.session.add(user)
    db.session.commit()

    return user


# * Image upload and retrieval * #

def upload_image(input_image, notes, user_id, board_id, private=False, upload_dir="uploads", file_or_url="url"):
    # We want to know what the last image_id was so that we can use it for the image's filename
    last_image_id = db.session.query(Image.image_id).order_by(Image.image_id.desc()).limit(1).scalar()
    if not last_image_id:
        image_id = "1"
    else:
        image_id = str(last_image_id + 1)

    # The user could supply a file or a URL.
    if file_or_url == "url":
        # Run some checks on the URL (e.g. file types)
        if not upload_url_checker(input_image):
            return False
        else:
            # Grab the filename from the url
            # These days Imgur does stuff like this:
            # https://i.imgur.com/U0vI1I3_d.webp?maxwidth=1520&fidelity=grand
            # Removing the parameters gives a thumbnail, so it must be included
            # Extract the file extension - this will be handy later if wanting to recompress images
            filename_without_params = os.path.basename(urlparse(input_image).path)
            filename_without_params = secure_filename(filename_without_params)
            file_extension = os.path.splitext(filename_without_params)[1].lower()

            # fetch the file
            # This is complicated by needing user-agent stuff to stop webservers immediately ignoring the request
            image_request = urllib.request.Request(input_image,
                                                   headers={'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'})
            try:
                response = urllib.request.urlopen(image_request)
            except HTTPError as exc:
                logging.debug(f"Failed to request file: {exc}")
                return False
            # Assuming all goes well, output it to a file
            # with open(f"./static/images/{image_id}{file_extension}", "wb") as file:)
            with open(f"{upload_dir}/{image_id}{file_extension}", "wb") as file:
                file.write(response.read())
            url = input_image
    else:
        # Deal with a local file instead
        logging.info(f"File to add: {input_image.filename}")
        input_image.filename = secure_filename(input_image.filename)
        file_extension = os.path.splitext(input_image.filename)[1].lower()
        if not uploaded_file_checker(input_image.filename):
            logging.debug(f"Failed to save file. File type not permitted ({file_extension})")
            return False
        # Save the file locally
        try:
            input_image.save(os.path.join(upload_dir, f"{image_id}{file_extension}"))
        except Exception as exc:
            logging.debug(f"Failed to save file: {exc}")
            return False
        # Assuming things go well, set the url value to blank:
        url = ""

    # Now that we have a file locally, attempt to recompress it and then stick it in the DB
    # Check if it can be recompressed
    if file_extension != ".gif" and file_extension != ".webp":
        if webp_if_larger(f"{upload_dir}/{image_id}{file_extension}"):
            # The Webp version is smaller - update the file extension
            file_extension = ".webp"

    # Generate the thumbnail
    thumbnail_generator(f"{upload_dir}/{image_id}{file_extension}")

    # Construct the image object - the url is a blank string if it's a file upload
    image = Image(
        thumbnail=f"thumbnails/{image_id}.webp",
        url=url,
        notes=notes,
        user_id=user_id,
        private=private,
        board_id=board_id,
        file_extension=file_extension
    )
    db.session.add(image)
    db.session.commit()

    # If the board has no images, make this image the thumbnail
    if len(Image.query.filter(Image.board_id == board_id).all()) == 1:
        board = Board.query.filter(Board.board_id == board_id).first()
        board.thumbnail = f"{image_id}{file_extension}"
        db.session.commit()

    return image


def upload_url_checker(requested_url):
    allowed_extensions = {'.webp', '.png', '.jpg', '.jpeg', '.gif'}
    filename = os.path.basename(urlparse(requested_url).path)
    file_extension = os.path.splitext(filename)[1]
    valid = True
    if file_extension.lower() not in allowed_extensions:
        valid = False
    return valid


def uploaded_file_checker(filename):
    allowed_extensions = {'.webp', '.png', '.jpg', '.jpeg', '.gif'}
    filename = os.path.basename(filename)
    file_extension = os.path.splitext(filename)[1].lower()
    valid = True
    if file_extension.lower() not in allowed_extensions:
        valid = False
    return valid


def thumbnail_generator(image_path):
    # Extract the necessary components to minimise dependencies on other bits of code
    upload_dir = os.path.split(image_path)[0]
    filename = Path(image_path).stem

    output_path = f"{upload_dir}/thumbnails/{filename}.webp"
    image = PillowImage.open(image_path)
    thumbnail_size = 640, 480
    image.thumbnail(thumbnail_size)
    image.save(output_path, 'webp', quality=80)


def board_thumbnail_set(board_id, image_id):
    """
    Update (or set) the thumbnail for a board (assuming that image is part of that board)

    :param (int) board_id: the board to update the thumbnail of
    :param (int) image_id: the image_id to set as the board thumbnail
    :return:
    """
    board = Board.query.get(board_id)
    image = Image.query.get(image_id)
    if image.board_id == board_id:
        board.thumbnail = f"{image_id}.webp"
        db.session.commit()
        return True
    else:
        return False


def webp_if_larger(image_path):
    """
    Recompress the image as Webp and keep it if it's smaller than the source

    :param image_path: local path to the input image
    :return: If the image has been recompressed, True, if not, False
    """
    source_file_size = os.path.getsize(image_path)
    output_path = f"{os.path.splitext(image_path)[0]}.webp"

    image = PillowImage.open(image_path)
    # Convert and save as WEBP (80% quality should be plenty)
    image.save(output_path, 'webp', quality=80)

    webp_file_size = os.path.getsize(output_path)
    if webp_file_size < source_file_size:
        # Delete the original
        os.remove(image_path)
        return True
    else:
        # Delete the webp
        os.remove(output_path)
        return False


def get_images_by_user(user_id):
    return Image.query.filter(Image.user_id == user_id).all()


# * Boards * #

def create_board(name, icon, hex_code, user_id):
    if Board.query.filter(Board.name == name).all():
        return False
    else:
        board = Board(
            name=name,
            icon=icon,
            hex_code=hex_code,
            user_id=user_id
        )
        db.session.add(board)
        db.session.commit()

        return board


def board_images_for_user(user_id, board_string):
    """
    Request a board by its name, supplying the user id associated with it.
    :param (int) user_id: the user who owns the board
    :param (str) board_string: the exact name of the board
    :return: (list) list of SQLAlchemy Image objects
    """
    # Each board has an associated user_id
    # Get a list of boards owned by them
    selected_board = Board.query.filter(Board.name == board_string, Board.user_id == user_id).first()
    if selected_board:
        # The user has that board, collect the images
        board_images = Image.query.filter(Image.board_id == selected_board.board_id).all()
    else:
        board_images = []
    return board_images


def board_images_for_shared_user(user_id, board_id):
    """
    If they have permission, return an image list, if not - don't.
    :param (int) user_id: the user_id for the requesting user, not the owner
    :param (int) board_id: the board the user is attempting to access
    :return:  A list of Image objects or False
    """
    selected_board = Board.query.get(board_id)
    shared_with_user_ids = []
    for user in selected_board.shared_with:
        shared_with_user_ids.append(user.user_id)
    if user_id in shared_with_user_ids:
        # This user has permission to view this board, collect the images
        return Image.query.filter(Image.board_id == selected_board.board_id).all()
    else:
        return False


def get_shareable_users(user_id, board_id):
    """
    Provides users that a given board can be shared with
    (i.e. not the owner and not users the board is already shared with)
    :param (int) user_id: owner user_id
    :param (int) board_id: board_id
    :return: (list) dictionaries with usernames/user_id values
    """
    shareable_users = []
    for user in User.query.filter().all():
        # Exclude the calling user
        if user.user_id != user_id:
            # Check if the board is already shared with that user
            if board_id not in get_board_ids_shared_with_user(user.user_id):
                user_details = {
                    "username": user.username,
                    "user_id": user.user_id
                }
                shareable_users.append(user_details)
    return shareable_users


def delete_image(user_id, image_id, upload_dir="uploads"):
    # If the user has permission, delete the image
    image = Image.query.filter(Image.image_id == image_id, Image.user_id == user_id).first()
    if image:
        board = Board.query.get(image.board_id)
        if f"{image.image_id}{image.file_extension}" == board.thumbnail:
            # This image is the board's thumbnail - we should replace the board's thumbnail
            # It might be present already - it's really not worth checking
            shutil.copyfile("./static/img/no_thumbnail.webp", f"{upload_dir}/no_thumbnail.webp")
            board.thumbnail = "no_thumbnail.webp"
        os.remove(f"{upload_dir}/{image_id}{image.file_extension}")
        os.remove(f"{upload_dir}/thumbnails/{image_id}.webp")
        db.session.delete(image)
        db.session.commit()
        return True
    else:
        return False


def delete_board(user_id, board_string, upload_dir="uploads"):
    """
    Delete a board, assuming the calling user owns the board.
    :param (int) user_id: board owner's user id
    :param (str) board_string: name of the board
    :param (str) upload_dir: where the images for the board live
    :return: (bool)
    """
    logging.info(f"Board to deletion for [{board_string}] requested by [{User.query.get(user_id).username}]")
    selected_board = Board.query.filter(Board.name == board_string, Board.user_id == user_id).first()
    if not selected_board:
        return False
    board_images = Image.query.filter(Image.board_id == selected_board.board_id).all()
    for image in board_images:
        delete_image(user_id, image.image_id, upload_dir=upload_dir)
    db.session.delete(selected_board)
    db.session.commit()
    return True
