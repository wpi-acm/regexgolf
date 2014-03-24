from regexgolf.db import db

class Challenges(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String())
    description = db.Column(db.String())
    date = db.Column(db.DateTime())

    def __repr__(self):
        return '<Challenge %r>' % self.name
