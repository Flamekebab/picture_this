from flask import Flask, render_template, request, flash, redirect, session, url_for, send_from_directory
import jinja2
import os
from model import connect_to_db
import helpers
import logging


app = Flask(__name__)
app.secret_key = os.environ["PT_SECRET_KEY"]  # use key exported from secrets.sh or set an environment variable
app.jinja_env.undefined = jinja2.StrictUndefined  # throw an error for an undefined Jinja var
connect_to_db(app)
app.config['UPLOAD_FOLDER'] = "uploads"
# 16 MB limit for images
app.config['MAX_CONTENT_LENGTH'] = 16 * 1000 * 1000

# Whilst doing dev work let's do some logging - I'm going to need it.
logging.basicConfig(level=logging.DEBUG)


@app.route('/uploads/<path:filename>')
def uploads(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# * RENDER PAGES * #


@app.route("/register")
def register():
    """Return home page."""

    return render_template("register.html")


@app.route("/log_in")
@app.route("/")
def show_login():
    """Return login page."""
    if 'user_id' in session:
        user = helpers.get_user_by_user_id(session['user_id'])
        return render_template("my_images.html", user=user, images=user.images)
    else:
        return render_template("login.html")


@app.route("/my_images")
def my_images():
    """Return My Images page - all the images a user has uploaded.
    Images are shown in reverse order - i.e. newest first"""
    if 'user_id' in session:
        user = helpers.get_user_by_user_id(session['user_id'])
    else:
        user = None

    return render_template("my_images.html", user=user, images=list(reversed(user.images)))


@app.route("/delete/<int:image_id>")
def delete_image(image_id):
    """
    Delete image by ID

    :param image_id: (int) ID of image to be deleted
    :return:
    """
    if 'user_id' in session:
        if helpers.delete_image(session['user_id'], image_id, upload_dir=app.config['UPLOAD_FOLDER']):
            message = "Image deleted successfully"
        else:
            message = "Failed to delete image"
    else:
        message = "Login to delete images"

    flash(message, "message")
    return redirect(request.referrer)


@app.route("/board/<string:selected_board>")
def show_single_board(selected_board):
    """Return a board - restricted to boards the user has access to."""

    if 'user_id' in session:
        user = helpers.get_user_by_user_id(session['user_id'])
        board_images = helpers.board_images_for_user(session['user_id'], selected_board)
    else:
        user = None
        board_images = None

    return render_template("single_board.html", user=user, selected_board=selected_board, images=board_images)


@app.route("/upload")
def show_upload_page():
    """Return Upload page."""

    if 'user_id' in session:
        user = helpers.get_user_by_user_id(session['user_id'])
    else:
        user = None

    return render_template("upload.html", user=user)


@app.route("/boards")
def show_boards_page():
    """Return Boards page."""

    if 'user_id' in session:
        user = helpers.get_user_by_user_id(session['user_id'])
    else:
        user = None

    return render_template("boards.html", user=user)


# * API * #
# TODO: secure the API

@app.route('/api/register_user', methods=['POST'])
def register_new_user():
    """Add a new user to the database."""

    username = request.form['username']
    email = request.form['email']
    password = request.form['password']

    if helpers.check_username(username) is None and helpers.check_email(email) is None:
        # user = helpers.register_user(username, email, password)
        helpers.register_user(username, email, password)
        flash(f'Account created!')
        return redirect('/log_in')
    else:
        flash('Try again with a different username and email!')
        return redirect('/')


@app.route('/api/log_in', methods=['POST'])
def log_in_user():
    """Log in existing user."""

    email = request.form['email']
    password = request.form['password']

    if helpers.check_email(email) is None:
        flash(f"Email doesn't exist in database!")
        return redirect('/log_in')
    else:
        user = helpers.check_email(email)

    if user.check_password(password):
        # session['user'] = user
        session['user_id'] = user.user_id
        session['username'] = user.username
        flash('Successfully logged in!')
        return redirect(url_for("my_images"))
    else:
        flash('Incorrect password!')
        return redirect('/log_in')


@app.route('/api/log_out')
def log_out():
    session.clear()
    flash('Logout successful.')
    return redirect('/')


@app.route('/api/upload', methods=['POST'])
def user_upload_from_form():
    # We should probably require some login credentials here..
    app.logger.debug(f"{request.form}")

    notes = request.form['notes']
    user_id = session['user_id']
    board_id = request.form['board_id']
    # This may or may not be used but is always present
    url = request.form['url']

    # Currently this isn't implemented
    if 'private' in request.form:
        private = True
    else:
        private = False

    if "attached-file" in request.files and request.form['file-or-url'] == "file":
        if helpers.upload_image(
                request.files['attached-file'], notes, user_id, private, board_id, app.config['UPLOAD_FOLDER'], "file"):
            flash('Image added!')
        else:
            flash('Upload failed')
    else:
        if helpers.upload_image(url, notes, user_id, private, board_id, app.config['UPLOAD_FOLDER'], "url"):
            flash('Image added!')
        else:
            flash('Upload failed')

    return redirect('/my_images')


@app.route('/api/add_board', methods=['POST'])
def add_board_from_form():
    name = request.form['name']
    icon = request.form['icon']
    color = '#e0a356'  # TODO: make this dynamic
    user_id = request.form['user_id']

    helpers.create_board(name, icon, color, user_id)

    flash('Board created successfully')

    if 'user_id' in session:
        user = helpers.get_user_by_user_id(session['user_id'])
    else:
        user = None

    return render_template("upload.html", user=user)


if __name__ == "__main__":
    # "PT" = 16-20 (A=1, B=2)
    app.run(debug=True, host="0.0.0.0", port=1620)
