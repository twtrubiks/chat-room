from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:xxxxx@localhost/db'

db = SQLAlchemy(app)
migrate = Migrate(app, db)

manager = Manager(app)
manager.add_command('db', MigrateCommand)


class UserAccounts(db.Model):
    __tablename__ = 'UserAccounts'

    Id = db.Column(db.Integer, primary_key=True)
    UserName = db.Column(db.String(64), unique=True)
    Password = db.Column(db.String(64))
    MugShot = db.Column(db.String(64))
    CreateDate = db.Column(db.DateTime)
    ModifiedDate = db.Column(db.DateTime)

    def __init__(self,
                 user_name,
                 password,
                 mugshot,
                 create_date=datetime.now(),
                 modified_date=datetime.now()):
        self.UserName = user_name
        self.Password = self.psw_to_md5(password)
        self.MugShot = mugshot
        self.CreateDate = create_date
        self.ModifiedDate = modified_date

    @staticmethod
    def psw_to_md5(str_psw):
        import hashlib
        if not str_psw:
            return None
        else:
            m = hashlib.md5(str_psw.encode(encoding='utf-8'))
            return m.hexdigest()


class Message(db.Model):
    __tablename__ = 'Message'

    Id = db.Column(db.Integer, primary_key=True)
    UserName = db.Column(db.String(64))
    Messages = db.Column(db.Text)
    CreateDate = db.Column(db.DateTime)

    def __init__(self,
                 user_name,
                 messages,
                 create_date):
        self.UserName = user_name
        self.Messages = messages
        self.CreateDate = create_date


if __name__ == '__main__':
    manager.run()
