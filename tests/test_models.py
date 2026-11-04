import hashlib
from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError

from dbModel import Message, UserAccounts, db


def md5(s):
    return hashlib.md5(s.encode('utf-8')).hexdigest()


class TestPswToMd5:
    def test_known_digest(self):
        assert UserAccounts.psw_to_md5('test') == '098f6bcd4621d373cade4e832627b4f6'

    def test_unicode_is_utf8_encoded(self):
        assert UserAccounts.psw_to_md5('密碼') == md5('密碼')

    @pytest.mark.parametrize('empty', ['', None])
    def test_empty_password_returns_none(self, empty):
        assert UserAccounts.psw_to_md5(empty) is None


class TestUserAccounts:
    def test_init_hashes_password_and_sets_fields(self):
        before = datetime.now()
        user = UserAccounts(user_name='alice', password='secret', mugshot='a.png')
        after = datetime.now()

        assert user.UserName == 'alice'
        assert user.Password == md5('secret')
        assert user.MugShot == 'a.png'
        assert before <= user.CreateDate <= after
        # 沒給日期時兩者應該是同一個時間點
        assert user.ModifiedDate == user.CreateDate

    def test_init_keeps_explicit_dates(self):
        created = datetime(2020, 1, 2, 3, 4, 5)
        modified = datetime(2021, 6, 7, 8, 9, 10)
        user = UserAccounts('alice', 'secret', 'a.png', create_date=created, modified_date=modified)

        assert user.CreateDate == created
        assert user.ModifiedDate == modified

    def test_user_name_is_unique(self, flask_app):
        with flask_app.app_context():
            db.session.add(UserAccounts('alice', 'secret', 'default.jpg'))
            db.session.commit()
            db.session.add(UserAccounts('alice', 'other', 'default.jpg'))
            with pytest.raises(IntegrityError):
                db.session.commit()
            db.session.rollback()


class TestMessage:
    def test_init_sets_fields(self):
        created = datetime(2020, 1, 2, 3, 4, 5)
        message = Message(user_name='alice', messages='hello', create_date=created)

        assert message.UserName == 'alice'
        assert message.Messages == 'hello'
        assert message.CreateDate == created

    def test_persists(self, flask_app):
        created = datetime(2020, 1, 2, 3, 4, 5)
        with flask_app.app_context():
            db.session.add(Message('alice', 'hello', created))
            db.session.commit()
            saved = Message.query.one()
            assert (saved.UserName, saved.Messages, saved.CreateDate) == ('alice', 'hello', created)
