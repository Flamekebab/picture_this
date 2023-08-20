import os
import urllib.request
from urllib.parse import urlparse
from PIL import Image as PillowImage
from werkzeug.utils import secure_filename
import logging
from model import db, User, Image, Tag

logging.basicConfig(level=logging.DEBUG)


# * General queries * #

def get_all_users():
    return User.query.all()


def get_user_by_user_id(user_id):
    return User.query.filter(User.user_id == user_id).first()


# * User registration & login * #

def check_username(username):
    """Check whether given username exists in users table."""
    return User.query.filter(User.username == username).first()


def check_email(email):
    """Check whether given email exists in users table."""
    return User.query.filter(User.email == email).first()


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

def upload_image(input_image, notes, user_id, private=False, tag_id=None, upload_dir="uploads", file_or_url="url"):
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
            response = urllib.request.urlopen(image_request)
            # Assuming all goes well, output it to a file
            if response.status == 200:
                # with open(f"./static/images/{image_id}{file_extension}", "wb") as file:)
                with open(f"{upload_dir}/{image_id}{file_extension}", "wb") as file:
                    file.write(response.read())
                url = input_image
            else:
                return False
    else:
        # Deal with a local file instead
        logging.info(f"File to add: {input_image.filename}")
        input_image.filename = secure_filename(input_image.filename)
        file_extension = os.path.splitext(input_image.filename)[1].lower()
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

    # Construct the image object - the url is a blank string if it's a file upload
    image = Image(
        url=url,
        notes=notes,
        user_id=user_id,
        private=private,
        tag_id=tag_id,
        file_extension=file_extension
    )
    db.session.add(image)
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


# * Tags * #

def create_tag(name, icon, hex_code, user_id):
    tag = Tag(
        name=name,
        icon=icon,
        hex_code=hex_code,
        user_id=user_id
    )
    db.session.add(tag)
    db.session.commit()

    return tag


def tagged_images_for_user(user_id, tag_string):
    # Each tag has an associated user_id
    # Get a list of tags by that name
    selected_tag = Tag.query.filter(Tag.name == tag_string, Tag.user_id == user_id).first()
    if selected_tag:
        # The user has that tag, collect the images
        tagged_images = Image.query.filter(Image.tag_id == selected_tag.tag_id).all()
    else:
        tagged_images = []
    return tagged_images


def delete_image(user_id, image_id, upload_dir="uploads"):
    # If the user has permission, delete the image
    image = Image.query.filter(Image.image_id == image_id, Image.user_id == user_id).first()
    if image:
        os.remove(f"{upload_dir}/{image_id}{image.file_extension}")
        db.session.delete(image)
        db.session.commit()
        return True
    else:
        return False
