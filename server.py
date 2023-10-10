from flask import Flask, render_template, request, flash, redirect, session, url_for, send_from_directory
import jinja2
import os
from model import connect_to_db
import helpers
import logging

app = Flask(__name__)
app.secret_key = os.environ["PT_SECRET_KEY"]  # use key exported from secrets.sh or set an environment variable
app.jinja_env.undefined = jinja2.StrictUndefined  # throw an error for an undefined Jinja var
# If we're running tests then set the flag so that a different database is used
if "PT_TESTING_MODE" in os.environ and os.environ['PT_TESTING_MODE']:
    app.config['TESTING'] = True
    app.config['UPLOAD_FOLDER'] = "test_uploads"
else:
    app.config['UPLOAD_FOLDER'] = "uploads"

connect_to_db(app)

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
        return render_template("my_images.html", user=user, images=list(reversed(user.images)))
    else:
        return render_template("login.html")


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

    flash(message)
    return redirect(request.referrer)


@app.route("/board/<string:username>/<string:selected_board>")
def show_single_board(selected_board, username):
    """Return a board - restricted to boards the user has access to.

    :param selected_board: (str) name of the board (Board.name)
    :param username: (str) name of the board's owner (User.username)
    """

    if 'user_id' in session:
        # Access to the board is allowed if the user owns the board or is in the shared list
        # First let's get the relevant ids
        owner_id = helpers.get_user_id_by_username(username)
        board_id = helpers.get_board_id_by_board_name(selected_board, owner_id)

        accessing_user = helpers.get_user_by_user_id(session['user_id'])

        if session['user_id'] == owner_id:
            # If it's the owner accessing it, show who it's shared with
            shared_with = helpers.get_shared_with(
                helpers.get_board_id_by_board_name(selected_board, session['user_id']),
                session['user_id']
            )
            # Collect the images from the user directly
            board_images = helpers.board_images_for_user(session['user_id'], selected_board)
        else:
            # This isn't their board, it's shared with them - we won't show who else it's shared with
            shared_with = []
            # If they don't have permission this will simply return False
            board_images = helpers.board_images_for_shared_user(session['user_id'], board_id)
        return render_template("single_board.html",
                               user=accessing_user,
                               selected_board=selected_board,
                               images=board_images,
                               shared_with=shared_with,
                               owner_username=username)
    else:
        return render_template("login.html")


@app.route("/delete_board/<string:username>/<string:selected_board>")
def delete_board(selected_board, username):
    """Delete a board"""

    if 'user_id' in session:
        if helpers.delete_board(session['user_id'], selected_board, upload_dir=app.config['UPLOAD_FOLDER']):
            flash(f"{selected_board} deleted!")
        else:
            flash(f"Problem encountered deleting {selected_board}!")
        return redirect(url_for("show_boards_page"))
    else:
        flash("Login to delete a board")
        return render_template("login.html")


# TODO: Share API board function - /api/share_board
@app.route("/share_board/<string:username>/<string:selected_board>")
def share_board(selected_board, username):
    """
    Take the user to a page where they can share their board with other users
    :param selected_board: board to share
    :param username: username of owner
    :return:
    """
    if 'user_id' in session:
        accessing_user = helpers.get_user_by_user_id(session['user_id'])
        board_id = helpers.get_board_id_by_board_name(selected_board, accessing_user.user_id)
        # Potential sharers is a list of dictionaries
        potential_sharers = helpers.get_shareable_users(accessing_user.user_id, board_id)
        if accessing_user.username == username:
            return render_template("share_board.html",
                                   user=accessing_user,
                                   selected_board=selected_board,
                                   potential_sharers=potential_sharers
                                   )
    else:
        flash("Login to share boards")
        return render_template("login.html")

# TODO: Unshare board function
# TODO: Leave board function


@app.route("/upload")
@app.route("/upload/<string:username>/<string:selected_board>")
def show_upload_page(username="", selected_board=""):
    """Return Upload page."""

    # To handle uploading to shared boards we need to get a bit complicated
    # owner_id = helpers.get_user_id_by_username(username)
    if 'user_id' in session:
        user = helpers.get_user_by_user_id(session['user_id'])
        available_boards = []
        for board in user.boards:
            board_object = {"name": board.name,
                            "board_id": board.board_id}
            available_boards.append(board_object)

        # They also might have some boards shared with them
        shared_board_ids = helpers.get_board_ids_shared_with_user(session['user_id'])
        for board_id in shared_board_ids:
            board_object = {"name": helpers.get_board_name_by_board_id(board_id),
                            "board_id": board_id}
            available_boards.append(board_object)

        return render_template("upload.html", user=user, available_boards=available_boards, upload_to=selected_board)
    else:
        return render_template("login.html")


@app.route("/boards")
def show_boards_page():
    """Return Boards page."""

    if 'user_id' in session:
        user = helpers.get_user_by_user_id(session['user_id'])
        # Get a list of board_ids that are shared with the user
        board_ids = helpers.get_board_ids_shared_with_user(session['user_id'])
        shared_boards = []
        for board_id in board_ids:
            board = helpers.get_board_from_id(board_id)
            board.username = helpers.get_user_by_user_id(board.user_id).username
            shared_boards.append(board)
        return render_template("boards.html", user=user, shared_boards=shared_boards)
    else:
        return render_template("login.html")


# * API * #

@app.route('/api/register_user', methods=['POST'])
def register_new_user():
    """Add a new user to the database."""

    username = request.form['username']
    email = request.form['email']
    password = request.form['password']

    if helpers.check_username(username) is None and helpers.check_email(email) is None:
        helpers.register_user(username, email, password)
        flash("Account created!")
        return render_template("login.html")
    else:
        flash('Try again with a different username and email!')
        return redirect('/')


@app.route('/api/log_in', methods=['POST'])
def log_in_user():
    """Log in existing user."""

    email = request.form['email']
    password = request.form['password']

    if helpers.check_email(email) is None:
        flash("Email doesn't exist in database!")
        return render_template("login.html")
    else:
        user = helpers.check_email(email)

    if user.check_password(password):
        session['user_id'] = user.user_id
        session['username'] = user.username
        flash('Successfully logged in!')
        return redirect(url_for("my_images"))
    else:
        flash('Incorrect password!')
        return render_template("login.html")


@app.route('/api/log_out')
def log_out():
    session.clear()
    flash('Logout successful.')
    return redirect('/')


# TODO: Handle uploads to shared boards
@app.route('/api/upload', methods=['POST'])
def user_upload_from_form():
    # Debug the form output
    # app.logger.debug(f"{request.form}")
    if 'user_id' in session:
        user_id = session['user_id']
    else:
        return render_template("login.html")

    notes = request.form['notes']

    # They've asked to upload to this board - we should check if they're actually allowed
    board_id = int(request.form['board_id'])
    owned_boards = helpers.get_user_board_ids(user_id)
    shared_boards = (helpers.get_board_ids_shared_with_user(user_id))
    available_boards = owned_boards + shared_boards
    if board_id not in available_boards:
        # Hey, what are you trying to pull?
        flash(f"You do not have permission to upload to that board! (board_id {board_id})")
        return redirect(url_for("show_upload_page"))

    # This may or may not be used but is always present
    url = request.form['url']

    # Currently this isn't implemented
    if 'private' in request.form:
        private = True
    else:
        private = False

    if "attached-file" in request.files and request.form['file-or-url'] == "file":
        if helpers.upload_image(
                request.files['attached-file'], notes, user_id, board_id, private, app.config['UPLOAD_FOLDER'], "file"):
            flash('Image added!')
        else:
            flash('Upload failed')
    else:
        if helpers.upload_image(url, notes, user_id, board_id, private, app.config['UPLOAD_FOLDER'], "url"):
            flash('Image added!')
        else:
            flash('Upload failed')
    # Redirect the user back to the board they uploaded from
    # The username may not be theirs - they might have uploaded to a shared board
    username = helpers.get_board_owner(board_id).username
    board_name = helpers.get_board_name_by_board_id(board_id)
    return redirect(f"/board/{username}/{board_name}")


@app.route('/api/add_board', methods=['POST'])
def add_board_from_form():
    if 'user_id' in session:
        user = helpers.get_user_by_user_id(session['user_id'])
        user_id = session['user_id']
    else:
        return render_template("login.html")

    name = request.form['name']
    icon = request.form['icon']
    color = '#e0a356'  # Not sure if this is relevant anymore - it was when boards were tags

    if helpers.create_board(name, icon, color, user_id):
        flash("Board created successfully")
        return redirect(url_for("show_upload_page"))
    else:
        flash(f"A board called {name} already exists")
        return redirect(url_for("show_boards_page"))


if __name__ == "__main__":
    # "PT" = 16-20 (A=1, B=2)
    app.run(debug=True, host="0.0.0.0", port=1620)
