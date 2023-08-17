import os
import urllib.request
from urllib.parse import urlparse
from model import db, User, Image, Tag


##### * General queries * #####

def get_all_users():
    return User.query.all()


def get_user_by_user_id(user_id):
    return User.query.filter(User.user_id == user_id).first()


##### * User registration & login * #####

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


##### * Image upload and retrieval * #####

def upload_image(url, notes, user_id, private=False, tag_id=None):
    # Grab the filename from the url
    image_filename = os.path.basename(urlparse(url).path)
    # Extract the file extension - this will be handy later if wanting to recompress images
    file_extension = os.path.splitext(image_filename)[1]

    # Then we want to know what the last image_id was so that we can use it for the image's filename
    last_image_id = db.session.query(Image.image_id).order_by(Image.image_id.desc()).limit(1).scalar()
    if not last_image_id:
        image_id = "1"
    else:
        image_id = str(last_image_id + 1)

    # fetch the file - call it 1.something for this proof of concept
    # This is complicated by needing user-agent stuff to stop webservers immediately ignoring the request
    image_request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'})
    response = urllib.request.urlopen(image_request)
    # Assuming all goes well, output it to a file
    if response.status == 200:
        pass
        with open(f"./static/images/{image_id}{file_extension}", "wb") as file:
            file.write(response.read())
    else:
        # This should probably be replaced with raising an exception when things are further along
        print("Failed to grab image")

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


def get_images_by_user(user_id):
    return Image.query.filter(Image.user_id == user_id).all()


##### * Tags * #####

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


def delete_image(user_id, image_id):
    # If the user has permission, delete the image
    image = Image.query.filter(Image.image_id == image_id, Image.user_id == user_id).first()
    if image:
        os.remove(f"./static/images/{image_id}{image.file_extension}")
        db.session.delete(image)
        db.session.commit()
        return True
    else:
        return False
