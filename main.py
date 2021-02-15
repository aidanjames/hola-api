from flask import Flask, render_template, redirect, url_for, flash, abort, jsonify, request
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
import os
import smtplib
from datetime import datetime
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, URL, Email
from functools import wraps
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")


# CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "sqlite:///blog.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# LOGIN MANAGER
login_manager = LoginManager()
login_manager.init_app(app)


# CONFIGURE TABLES
class Consumer(UserMixin, db.Model):
    __tablename__ = "consumers"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    key = db.Column(db.String(100), unique=True, nullable=True)
    requests_this_month = db.Column(db.Integer)
    last_request = db.Column(db.Date, nullable=True)
    email_verified = db.Column(db.Boolean)


db.create_all()


# TODO create a form to generate a new API user
class CreateConsumerForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()], render_kw={"autofocus": True, "autocomplete": 'off'})
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Register")


class LogInForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()], render_kw={"autofocus": True, "autocomplete": 'off'})
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log in")


def send_validation_email():
    # TODO Ensure user is signed in
    # TODO Generate a url for the verification
    # TODO Add email credentials to environment variables
    if current_user:
        message = f"Subject: Please validate your email\n\n" \
                  f"Hi! Thanks for signing up to use the Hola API.\n\n" \
                  f"Please validate your email address by clicking or copy/pasting the link below:\n\n" \
                  f"http://tbc{current_user.key}"
        with smtplib.SMTP(os.getenv("SMTP_SERVER")) as connection:
            connection.starttls()
            connection.login(user=os.getenv("MY_EMAIL"), password=os.getenv("EMAIL_PASSWORD"))
            connection.sendmail(from_addr=os.getenv("MY_EMAIL"),
                                to_addrs=os.getenv("MY_EMAIL"),
                                msg=message)


@login_manager.user_loader
def user_loader(user_id):
    return db.session.query(Consumer).get(user_id)


def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_anonymous:
            return abort(403)
        if current_user.id != 1:
            return abort(403)
        return f(*args, **kwargs)

    return decorated_function


@app.route('/')
def home():
    # TODO Create index.html with link to documentation and link to generate API key
    return render_template('index.html')


@app.route('/documentation')
def documentation():
    # TODO Create documentation.html page
    return render_template('documentation.html')


@app.route('/api-key')
def api_key():
    # TODO create a page to show/generate API key
    # TODO create api-key.html page
    return render_template('api-key.html')


@app.route('/register', methods=["GET", "POST"])
def register():
    form = CreateConsumerForm()
    if form.validate_on_submit():
        if db.session.query(Consumer).filter_by(email=form.email.data).first():
            flash("Email already exists, log in!")
            return redirect(url_for("login"))

        hashed_password = generate_password_hash(
            form.password.data,
            method='pbkdf2:sha256',
            salt_length=8
        )

        new_consumer = Consumer()
        new_consumer.email = form.email.data
        new_consumer.password = hashed_password
        new_consumer.requests_this_month = 0
        new_consumer.key = uuid.uuid1()
        new_consumer.email_verified = False

        db.session.add(new_consumer)
        db.session.commit()

        login_user(new_consumer)
        return redirect(url_for("home"))
    # TODO create register.html page
    return render_template("register.html", form=form, current_user=current_user)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LogInForm()
    if form.validate_on_submit():
        user = db.session.query(Consumer).filter_by(email=form.email.data).first()
        if not user:
            flash("Email not registered, please try again.")
            return redirect(url_for("login"))
        elif not check_password_hash(user.password, form.password.data):
            flash("Invalid password, please try again.")
            return redirect(url_for("login"))
        else:
            login_user(user)
            return redirect(url_for("home"))
    # TODO Create login.html page
    return render_template("login.html", form=form, current_user=current_user)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route("/verify")
def contact():
    key = request.args.get('key')
    if current_user:
        user_api_key = current_user.key
        if key == user_api_key:
            # TODO create verified.html page
            return render_template("verified.html")
    # TODO create error.html
    return render_template('error.html')


@app.route("/consumers")
@admin_only
def view_all_consumers():
    # TODO Create consumers.html page
    consumers = Consumer.query().all()
    return render_template("consumers.html", conumers=consumers)


@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}


# RESTful API routes
@app.route("/random")
def random():
    my_dict = {
        "es": "Hola",
        "en": "Hello"
    }
    return jsonify(response=my_dict)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
