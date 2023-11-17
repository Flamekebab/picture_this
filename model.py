from flask_sqlalchemy import SQLAlchemy
import bcrypt

db = SQLAlchemy()

# By doing things this way we prevent invalid user_id values in the shared boards table
# We can also easily show which boards are shared with a user
shared_boards = db.Table(
    'shared_boards',
    db.Column('board_id', db.Integer, db.ForeignKey('boards.board_id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('users.user_id'), primary_key=True)
)


class User(db.Model):
    """Data model for a user."""

    __tablename__ = "users"

    user_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    username = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(50), nullable=False)
    password_hashed = db.Column(db.LargeBinary(128), nullable=False)

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
    shared_with = db.relationship('User', secondary=shared_boards,
                                  backref=db.backref('shared_boards', lazy='dynamic'))

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
def connect_to_db(flask_app, echo=True):
    # If we're in testing mode don't use the production DB!
    if flask_app.config['TESTING']:
        flask_app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///test_database.db"
    else:
        flask_app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///pt_database.db"
    # flask_app.config['SQLALCHEMY_ECHO'] = echo
    flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.app = flask_app
    db.init_app(flask_app)

    print(f"Connected to {flask_app.config['SQLALCHEMY_DATABASE_URI']}")


if __name__ == '__main__':
    pass
    # from server import app
    #
    # connect_to_db(app)
    # This file can be run to debug database queries
    # Y'know... here
    # image = Image.query.filter(Image.image_id == 2, Image.user_id == 1).first()
    # other_images = Image.query.filter(Image.board_id == image.board_id, Image.image_id != image.image_id).all()
    # print(other_images)
    # db.session.commit()
