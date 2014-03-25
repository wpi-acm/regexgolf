#!/usr/bin/env python

import simpleldap
import ldap
import re
from flask import Flask, render_template, request, redirect, url_for, g, \
    flash
from flask.ext.admin import Admin, BaseView, expose
from flask.ext.admin.contrib.sqla import ModelView
from flask.ext.login import LoginManager, login_user, UserMixin, \
    login_required, logout_user, current_user
from flask.ext.migrate import Migrate, MigrateCommand
from flask.ext.script import Manager
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func, and_
from wtforms.fields import TextAreaField

import config
from forms import *

app = Flask(__name__)
app.config.from_object(config)


# DATABASES
db = SQLAlchemy(app)
migrate = Migrate(app, db)

manager = Manager(app)
manager.add_command('db', MigrateCommand)


# MODELS
class Challenge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String())
    description = db.Column(db.String())
    details = db.Column(db.String())
    date = db.Column(db.DateTime())
    positive_cases = db.Column(db.String())
    negative_cases = db.Column(db.String())
    solutions = db.relationship('Solution', backref='challenge',
                                lazy='dynamic')

    def num_tests(self):
        return (len(self.positive_cases.split('\n')) +
                len(self.negative_cases.split('\n')))

    def verify(self, regex):
        try:
            # Clean up regex
            regex = regex.strip('/').rstrip('/i')
            prog = re.compile(regex)
            for test in self.positive_cases.split('\n'):
                assert prog.search(test) is not None
            for test in self.negative_cases.split('\n'):
                assert prog.search(test) is None
        except AssertionError:
            return False
        return True

    def get_others_solutions(self, user):
        my_score = user.get_solution(self).score()
        return Solution.query.filter(
            and_(func.length(Solution.value)) >= my_score,
                 Solution.user != user.username,
                 Solution.challenge == self).all()

    def is_solved(self):
        return len(Solution.query.filter_by(challenge=self).all()) > 0

    def best_solution(self):
        return Solution.query.filter_by(challenge=self).order_by(func.length(Solution.value)).first()

    def __repr__(self):
        return '<Challenge %r>' % self.name


class Solution(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    challenge_id = db.Column(db.Integer, db.ForeignKey('challenge.id'))
    value = db.Column(db.String())
    user = db.Column(db.String())

    def __init__(self, user, challenge_id, solution):
        self.user = user.username
        self.challenge_id = challenge_id
        self.value = solution

    def score(self):
        return len(self.value.strip('/').rstrip('/i'))

    def __repr__(self):
        return '<Solution for %r: %r>' % (self.challenge_id, self.user)


# ADMIN
class RegexGolfModelView(ModelView):

    form_overrides = dict(details=TextAreaField,
                          positive_cases=TextAreaField,
                          negative_cases=TextAreaField)

    def is_accessible(self):
        return (current_user.is_authenticated() and current_user.is_admin())


admin = Admin(app, name="WPI ACM Regex Golf", endpoint='admin')
admin.add_view(RegexGolfModelView(Challenge, db.session))
admin.add_view(RegexGolfModelView(Solution, db.session))


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# AUTH
def ldap_fetch(uid=None, name=None, passwd=None):
    # try:
    result = None
    if name is not None and passwd is not None:
        # weird hack to auth with WPI CCC
        conn = simpleldap.Connection(
            config.LDAP_SERVER,
            port=config.LDAP_PORT,
            require_cert=False,
            dn=config.BIND_DN, password=config.LDAP_PASSWORD,
            encryption='ssl')
        res = conn.search('uid={0}'.format(name), base_dn=config.BASE_DN)
        dn = config.BIND_DN_FORMAT.format(res[0]['wpieduPersonUUID'][0])
        conn = simpleldap.Connection(
            config.LDAP_SERVER,
            port=config.LDAP_PORT,
            require_cert=False,
            dn=dn, password=passwd,
            encryption='ssl')
        if conn:
            result = res
    else:
        conn = simpleldap.Connection(config.LDAP_SERVER)
        result = conn.search(
            'uidNumber={0}'.format(uid),
            base_dn=config.BASE_DN)

    if result:
        return {
            'name': result[0]['givenName'][0],
            'uid': result[0]['uid'][0],
            'id': unicode(result[0]['uidNumber'][0]),
            'gid': int(result[0]['gidNumber'][0])
        }
    else:
        return None


class User(UserMixin):
    def __init__(self, uid=None, name=None, passwd=None):

        self.active = False

        ldapres = ldap_fetch(uid=uid, name=name, passwd=passwd)

        if ldapres is not None:
            self.name = ldapres['name']
            self.username = ldapres['uid']
            self.id = ldapres['id']
            # assume that a disabled user belongs to group 404
            if ldapres['gid'] != 404:
                self.active = True
            self.gid = ldapres['gid']

    def is_active(self):
        return self.active

    def is_admin(self):
        return self.username in config.ADMIN_USERNAMES

    def has_solved(self, challenge):
        solutions = Solution.query.filter_by(
            user=self.username, challenge=challenge).all()
        return len(solutions) > 0

    def get_id(self):
        return self.id

    def get_solution(self, challenge):
        return Solution.query.filter_by(
            user=self.username, challenge=challenge).first()


# MIDDLEWARE
@login_manager.user_loader
def load_user(userid):
    return User(uid=userid)


@app.before_request
def before_request():
    g.user = current_user


# ROUTES
@app.route('/')
@login_required
def home():
    challenges = Challenge.query.all()
    return render_template(
        'index.html', title="WPI ACM - Regex Golf", challenges=challenges)


@app.route('/challenge/<challenge_id>', methods=["GET", "POST"])
@login_required
def challenge(challenge_id):
    challenge = Challenge.query.get(challenge_id)
    if challenge is None:
        return redirect(url_for('home'))

    if request.method == "GET":
        return render_template(
            'challenge.html',
            title="#{} - {}".format(challenge_id, challenge.name),
            challenge=challenge)
    elif request.method == "POST":
        regex = request.data
        if challenge.verify(regex):
            existing_solution = Solution.query.filter_by(
                user=current_user.username, challenge_id=challenge_id)
            if existing_solution.first() is not None:
                existing_solution = existing_solution.first()
                existing_solution.value = regex
                db.session.commit()
            else:
                solution = Solution(current_user, challenge_id, regex)
                db.session.add(solution)
                db.session.commit()
            flash("Your submission has been received!")
            return url_for('home')
        return ""



@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated():
        return redirect(url_for('home'))
    form = LoginForm(request.form)
    if request.method == 'POST' and form.validate():
        user = User(name=form.username.data, passwd=form.password.data)
        if user.active is not False:
            login_user(user)
            # flash("Logged in successfully.")
            return redirect(url_for("home"))
    return render_template("login.html", form=form)


@app.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


if __name__ == '__main__':
    manager.run()
