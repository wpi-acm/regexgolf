#!/usr/bin/env python

import simpleldap
from flask import Flask, render_template, request, redirect, url_for, g
from flask.ext.admin import Admin, BaseView, expose
from flask.ext.admin.contrib.sqla import ModelView
from flask.ext.login import LoginManager, login_user, UserMixin, \
    login_required, logout_user, current_user
from flask.ext.migrate import Migrate, MigrateCommand
from flask.ext.script import Manager
from flask.ext.sqlalchemy import SQLAlchemy
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

    def num_tests(self):
        return (len(self.positive_cases.split('\n')) +
                len(self.negative_cases.split('\n')))

    def __repr__(self):
        return '<Challenge %r>' % self.name


# ADMIN
class RegexGolfModelView(ModelView):

    form_overrides = dict(details=TextAreaField,
                          positive_cases=TextAreaField,
                          negative_cases=TextAreaField)

    def is_accessible(self):
        return (current_user.is_authenticated() and current_user.is_admin())


admin = Admin(app, name="WPI ACM Regex Golf")
admin.add_view(RegexGolfModelView(Challenge, db.session))


login_manager = LoginManager()
login_manager.init_app(app)


# AUTH
def ldap_fetch(uid=None, name=None, passwd=None):
    try:
        if name is not None and passwd is not None:
            print 'here'
            l = simpleldap.Connection(config.LDAP_SERVER, port=636,
                require_cert=False,
                dn=config.BIND_DN, password=config.LDAP_PASSWORD,
                encryption='ssl')
            r = l.search('uid={0}'.format(name), base_dn=config.BASE_DN)
        else:
            l = simpleldap.Connection(config.LDAP_SERVER)
            r = l.search('uidNumber={0}'.format(uid), base_dn=config.BASE_DN)

        return {
            'name': r[0]['givenName'][0],
            'uid': r[0]['uid'][0],
            'id': unicode(r[0]['uidNumber'][0]),
            'gid': int(r[0]['gidNumber'][0])
        }
    except:
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

    def get_id(self):
        return self.id

    def is_admin(self):
        return self.username in config.ADMIN_USERNAMES


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


@app.route('/challenge/<challenge_id>')
def challenge(challenge_id):
    challenge = Challenge.query.get(challenge_id)
    return render_template(
        'challenge.html',
        title="#{} - {}".format(challenge_id, challenge.name),
        challenge=challenge)


@app.route("/login", methods=["GET", "POST"])
def login():
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
