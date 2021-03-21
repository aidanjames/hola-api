from sqlalchemy import exc
from flask import Flask, render_template, redirect, url_for, flash, abort, jsonify, request
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
import os
import smtplib
from datetime import datetime
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Email, EqualTo, Length
from functools import wraps
import uuid
from flask_bootstrap import Bootstrap
import flask_monitoringdashboard as dashboard
from selenium_translation_manager import SeleniumTranslationManger
from file_manager import FileManager
from story_manager import StoryManager

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
Bootstrap(app)

dashboard.config.init_from(file='/config.cfg')
dashboard.bind(app)

# CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "sqlite:///hola.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# LOGIN MANAGER
login_manager = LoginManager()
login_manager.init_app(app)

# TRANSLATION MANAGER
translator = None

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


class Words(db.Model):
    __tablename__ = 'words'
    es = db.Column(db.String(100), unique=True, primary_key=True)
    en = db.Column(db.String(100))


# db.create_all()


# --------- FORMS --------- #
class CreateConsumerForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(), EqualTo('email2', message='Emails must match')],
                        render_kw={"autofocus": True, "autocomplete": 'off'})
    email2 = StringField("Repeat Email")
    password = PasswordField("Password",
                             validators=[DataRequired(), EqualTo('confirm', message='Passwords must match')])
    confirm = PasswordField("Repeat Password")
    submit = SubmitField("Register")


class LogInForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()],
                        render_kw={"autofocus": True, "autocomplete": 'off'})
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log in")


class EditTranslationForm(FlaskForm):
    english = StringField("English translation", validators=[DataRequired(), Length(max=100, message="Max length 100")],
                          render_kw={"autofocus": True, "autocomplete": 'off'})
    submit = SubmitField("Save translation")


def send_validation_email():
    if current_user:
        message = f"Subject: Please validate your email\n\n" \
                  f"Hi! Thanks for signing up to use the Hola API.\n\n" \
                  f"Please validate your email address by clicking or copy/pasting the link below:\n\n" \
                  f"http://127.0.0.1:5000/verify?key={current_user.key}"
        with smtplib.SMTP(os.getenv("SMTP_SERVER")) as connection:
            connection.starttls()
            connection.login(user=os.getenv("MY_EMAIL"), password=os.getenv("EMAIL_PASSWORD"))
            connection.sendmail(from_addr=os.getenv("MY_EMAIL"),
                                to_addrs=current_user.email,
                                msg=message)


def valid_api_key(headers):
    try:
        key_from_header = headers['x-api-key']
        if key_from_header == os.getenv("ADMIN_KEY"):
            return True
        else:
            return False
        # consumer = Consumer.query.filter_by(key=key_from_header).first()
        # if consumer and (consumer.email_verified or consumer.id == 1):
        #     first_of_month = datetime.today().replace(day=1).date()
        #     if consumer.last_request and consumer.last_request < first_of_month:
        #         consumer.requests_this_month = 1
        #     else:
        #         consumer.requests_this_month = consumer.requests_this_month + 1
        #     consumer.last_request = datetime.now()
        #     db.session.commit()
        #     return True
        # else:
        #     return False
    except KeyError:
        return False


def save_translation(es, en):
    try:
        new_word = Words()
        new_word.es = es
        new_word.en = en

        db.session.add(new_word)
        db.session.commit()
    except exc.IntegrityError as e:
        print(f"Error saving translation: {e}")


@login_manager.user_loader
def user_loader(user_id):
    return db.session.query(Consumer).get(user_id)


def logged_in(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_anonymous:
            return abort(403)
        return f(*args, **kwargs)

    return decorated_function


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
    return render_template('index.html')


@app.route('/documentation')
def documentation():
    # TODO Create documentation.html page
    return render_template('documentation.html')


@app.route('/account')
@logged_in
def account():
    return render_template('account.html')


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
        new_consumer.key = str(uuid.uuid1())
        new_consumer.email_verified = False

        db.session.add(new_consumer)
        db.session.commit()

        login_user(new_consumer)
        return redirect(url_for("home"))
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
    return render_template("login.html", form=form, current_user=current_user)


@app.route('/confirm-delete')
@logged_in
def confirm_delete():
    return render_template('delete-account.html')


@app.route('/delete-account')
@logged_in
def delete_account():
    user_to_delete = current_user
    db.session.delete(user_to_delete)
    db.session.commit()
    logout_user()
    return redirect(url_for('home'))


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route("/verify")
@logged_in
def verify_email():
    key = request.args.get('key')
    if key:
        if current_user:
            if key == current_user.key:
                current_user.email_verified = True
                db.session.commit()
                return render_template("verified.html")
        return "Page not found", 404
    else:
        send_validation_email()
        return render_template("verify-email.html")


@app.route("/consumers")
@admin_only
def view_all_consumers():
    consumers = db.session.query(Consumer).all()
    return render_template("consumers.html", consumers=consumers)


@app.route('/translations')
@admin_only
def translations():
    words = db.session.query(Words)
    return render_template('translations.html', translations=words)


@app.route('/delete-translation')
@admin_only
def delete_translation():
    es = request.args.get('es')
    translation_to_delete = db.session.query(Words).filter_by(es=es).first()
    if translation_to_delete:
        db.session.delete(translation_to_delete)
        db.session.commit()
        return redirect(url_for('translations'))
    else:
        return "Cannot delete word", 403


@app.route('/edit-translation', methods=["GET", "POST"])
@admin_only
def edit_translation():
    es = request.args.get('es')
    translation_to_edit = Words.query.get(es)
    form = EditTranslationForm(english=translation_to_edit.en)
    if form.validate_on_submit():
        translation_to_edit.en = form.english.data
        db.session.commit()
        return redirect(url_for('translations'))
    else:
        return render_template('edit-translation.html', spanish= translation_to_edit.es, form=form)


@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}


# RESTful API routes
# TODO delete the following as it is for quick testing only
@app.route("/random")
def random():
    headers = request.headers
    if valid_api_key(headers):
        my_dict = {
            "es": "Hola",
            "en": "Hello"
        }
        return jsonify(response=my_dict)
    else:
        return "API Key not found", 403


@app.route("/translate")
def translate():
    global translator
    headers = request.headers

    if valid_api_key(headers):
        es = request.args.get('es')
        existing_translation = db.session.query(Words).filter_by(es=es).first()
        print(f"The value to translate is {es}")
        if existing_translation:
            print("We've got an existing translation in the database so we'll return that...")
            return_dict = {
                "en": existing_translation.en,
                "es": existing_translation.es
            }
            return jsonify(response=return_dict)
        elif es:
            print("We do not have an existing translation so we're gunna get one...")
            if not translator:
                translator = SeleniumTranslationManger()
            en = translator.translate(text=es, title="Words")
            save_translation(es=es, en=en)
            return_dict = {
                "en": en,
                "es": es
            }
            translator.close_webdriver()
            translator = None
            return jsonify(response=return_dict)
        else:
            return "No text to translate", 400
    else:
        return "API Key not found", 403


@app.route("/story")
def story():
    print("I'm in the story function")
    headers = request.headers
    title = request.args.get('title')
    print(f"The title is {title}")
    if valid_api_key(headers):
        my_story = StoryManager().fetch_story(story=title)
        story_title = my_story[0]
        story_paragraphs = my_story[1]

        translator = SeleniumTranslationManger()
        print("********ES*******")
        print(story_title)
        print("********EN*******")
        print(translator.translate(text=story_title, title=story_title))
        print("\n")

        for paragraph in story_paragraphs:
            print("********ES*******")
            print(paragraph)
            print("********EN*******")
            print(translator.translate(text=paragraph, title=story_title))
            print("\n")

        translator.close_webdriver()

        file_manager = FileManager()
        print(file_manager.return_story(story_title))

        return_value = {
            "story-title": f"{story_title}"
        }
        return jsonify(response=return_value)
    else:
        return "API Key not found", 403


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
