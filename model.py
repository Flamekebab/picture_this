from flask_sqlalchemy import SQLAlchemy
import bcrypt

db = SQLAlchemy()


class User(db.Model):
    """Data model for a user."""

    __tablename__ = "users"

    user_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    username = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(50), nullable=False)
    password_hashed = db.Column(db.LargeBinary(128), nullable=False)

    # images: a list of Image objects associated with User.
    # relationship is established in Image model.
    # boards: a list of Board objects associated with User.
    # relationship is established in Board model.

    def get_hash(password):
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(15))

    def check_password(self, password):
        encoded_password = password.encode("utf-8")
        return bcrypt.checkpw(encoded_password, self.password_hashed)

    def __repr__(self):
        """Display info about User."""

        return f'<User user_id={self.user_id}, username={self.username}, email={self.email}>'


class Board(db.Model):
    """Data model for a board."""

    __tablename__ = "boards"

    board_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    thumbnail = db.Column(db.String)
    name = db.Column(db.String(15), nullable=False)
    icon = db.Column(db.String(50), nullable=False)
    hex_code = db.Column(db.String(15), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)

    # images: a list of Image objects associated with Board.
    # relationship is established in Image model.

    # establishes foreign key as two-way relationship
    user = db.relationship('User', foreign_keys=[user_id], backref='boards')

    def __repr__(self):
        """Display info about Image."""

        return f'<Board board_id={self.board_id}, name={self.name}>'


class Image(db.Model):
    """Data model for an image."""

    __tablename__ = "images"

    image_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    thumbnail = db.Column(db.String)
    url = db.Column(db.String, nullable=False)
    file_extension = db.Column(db.String)
    notes = db.Column(db.String)
    private = db.Column(db.Boolean, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    board_id = db.Column(db.Integer, db.ForeignKey('boards.board_id'))

    # establishes foreign keys as two-way relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='images')
    board = db.relationship('Board', foreign_keys=[board_id], backref='images')

    def __repr__(self):
        """Display info about Image."""

        return f'<Image image_id={self.image_id}, url={self.url}>'


# Any SQLAlchemy compatible database should work and sqlite is fine as a starter
def connect_to_db(flask_app, db_uri='sqlite:///pt_database.db', echo=True):
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    # flask_app.config['SQLALCHEMY_ECHO'] = echo
    flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.app = flask_app
    db.init_app(flask_app)

    print('Connected to the db!')


if __name__ == '__main__':
    from server import app
    connect_to_db(app)
    # This file can be run to debug database queries
    # Y'know... here
