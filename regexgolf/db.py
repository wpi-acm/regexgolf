from flask.ext.sqlalchemy import SQLAlchemy

from regexgolf.app import app
from regexgolf.config import DATABASE_URI

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
db = SQLAlchemy(app)
