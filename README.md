# Picture This :heart_eyes: your virtual vision board

Picture This is a photo repository to store and categorize your favorite pics.


## Tech stack :books:  
* Python/Flask with Unittest and bcrypt
* SQL/SQLite
* SQLAlchemy ORM
* Jinja (HTML templating)
* CSS/Bootstrap


## The database model :card_index_dividers:

![app screenshot](/static/img/model_pt_v1.png)


## How it works :desktop_computer:

Users can create an account with a username, email, and password - passwords are hashed and salted using Python's **bcrypt** module and added to the **SQLite** database using **SQLAlchemy**.

![app screenshot](/static/img/pt_img_register.png)

When a user logs in, their email and password are checked against the database with the help of **bcrypt**, then they are directed to a view that shows all the images they've uploaded.

![app screenshot](/static/img/pt_gif_login.gif)

They can add new photos or boards, which will be committed to the database and rendered with Flask's **Jinja2** HTML templating.

![app screenshot](/static/img/pt_gif_tag.gif)


## Running this app :zap:

Requirements:
Python3

To run locally (*nix):

1. Clone this repository to your machine:

```
$ git clone https://github.com/coriography/picture_this
```

2. Create virtual environment (wherever, whatever name you like):

```
$ python3 -m venv pt_venv
```

3. Activate your virtual environment:

```
$ source pt_venv/bin/activate
```

4. Install dependencies:

```
$ pip3 install -r requirements.txt
```

5. Set a secret key to run Flask by creating /secrets.sh in your root directory:

![app screenshot](/static/img/secret_key.png)

6. Add your key to your environmental variables:

```
$ source secrets.sh
```

7. Run tests:

```
$ python3 tests.py
```

8. Create database

```
$ python3 initialise_db.py
```

9. (Optional) Populate the database with some demo data (NOT FOR PRODUCTION!)

```
$ python3 demo_data.py
```

10. Launch the server:

```
$ python3 server.py
```

11. Go to localhost:1620 in your browser

12. Create an account, or log in with existing account *guppy@thecat.com, badpw* if you added the demo data.

If you've logged in as the demo account and not logged out then the server will throw an error if you attempt to
access the site with an invalid session (e.g. if you've wiped the database without logging out).
You can use your browser's dev tools to manually clear the session.

## What's next? :thinking:

Rewritten by Flamekebab (as I'm not Cori!):

1. Shared boards
2. Tagging
3. Better security
4. Private images?

## About the developers :woman_technologist:

Originally built by [Cori Lint](https://github.com/coriography), with the help of Guppy the cat. :cat:

*Cori is cellist-turned-software engineer with a knack for motivating and inspiring others. As her career has evolved from performance, to production, to web design, to software engineering, she has continued to seek growth and creative solutions. Cori brings to the tech industry leadership abilities, persistence, focus, empathy, and good judgment, along with a strong set of technical skills and prior experience in web development. She is a Summa Cum Laude graduate of the University of Michigan, and an active member of Artists Who Code, an online community that advocates for creative professionals in the tech industry.*

Contact Cori on [LinkedIn](https://www.linkedin.com/in/cori-lint/)

Heavily modified by [Flamekebab](https://toot.wales/@Flamekebab), alas Molly the cat had to go long before I worked on this.

