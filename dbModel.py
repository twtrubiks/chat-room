from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


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
                 create_date=None,
                 modified_date=None):
        now = datetime.now()
        self.UserName = user_name
        self.Password = self.psw_to_md5(password)
        self.MugShot = mugshot
        self.CreateDate = create_date if create_date is not None else now
        self.ModifiedDate = modified_date if modified_date is not None else now

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
