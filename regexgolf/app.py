#!/usr/bin/env python

from flask import Flask, render_template
from flask.ext.admin import Admin, BaseView, expose
from flask.ext.admin.contrib.sqla import ModelView
from flask.ext.sqlalchemy import SQLAlchemy

from config import DATABASE_URI

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
db = SQLAlchemy(app)


class Challenge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String())
    description = db.Column(db.String())
    details = db.Column(db.String())
    date = db.Column(db.DateTime())
    positive_cases = db.Column(db.String())
    negative_cases = db.Column(db.String())

    def num_tests(self):
        return (len(self.positive_cases.split(',')) +
                len(self.negative_cases.split(',')))

    def __repr__(self):
        return '<Challenge %r>' % self.name


admin = Admin(app, name="WPI ACM Regex Golf")
admin.add_view(ModelView(Challenge, db.session))


@app.route('/')
def home():
    challenges = Challenge.query.all()
    return render_template(
        'index.html', title="WPI ACM - Regex Golf", challenges=challenges)


@app.route('/challenge/<challenge_id>')
def challenge(challenge_id):
    challenge = Challenge.query.get(challenge_id)
    return render_template(
        'challenge.html', challenge=challenge)



if __name__ == '__main__':
    app.run(debug=True)
