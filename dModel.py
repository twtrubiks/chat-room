from datetime import datetime
from Entity import *


class UserAccounts(db.Model):
    __tablename__ = 'UserAccounts'

    def __init__(self
                 , UserName
                 , Password
                 , MugShot
                 , CreateDate=datetime.now()
                 , ModifiedDate=datetime.now()
                 ):
        self.UserName = UserName
        self.Password = self.psw_to_md5(Password)
        self.MugShot = MugShot
        self.CreateDate = CreateDate
        self.ModifiedDate = ModifiedDate

    def update(self):
        db.session.commit()

    @classmethod
    def psw_to_md5(self, str_psw):
        import hashlib
        if str_psw == None:
            return None
        else:
            m = hashlib.md5(str_psw.encode(encoding='utf-8'))
            return m.hexdigest()


class Message(db.Model):
    __tablename__ = 'Message'

    def __init__(self
                 , UserName
                 , Messages
                 , CreateDate
                 ):
        self.UserName = UserName
        self.Messages = Messages
        self.CreateDate = CreateDate

    def update(self):
        db.session.commit()
