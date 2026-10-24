import functools
import io
import os
import tempfile

import pytest
from PIL import Image
from werkzeug.security import generate_password_hash

# app.py 在 import 時就會用 SQLALCHEMY_DATABASE_URI 建立 engine，
# 所以必須在 import app 之前把 DB 指到暫存檔，避免動到專案裡的 app.db。
_DB_DIR = tempfile.mkdtemp(prefix='chat-room-test-')
os.environ['CHAT_ROOM_DATABASE_URL'] = 'sqlite:///' + os.path.join(_DB_DIR, 'test.db')

import app as chat_app  # noqa: E402
from dbModel import UserAccounts, db  # noqa: E402
import dbModel  # noqa: E402


@pytest.fixture(autouse=True)
def fast_password_hash(monkeypatch):
    # scrypt 每次要 ~0.1 秒，測試裡換成低成本的 pbkdf2；check_password_hash 兩種格式都認得
    monkeypatch.setattr(dbModel, 'generate_password_hash',
                        functools.partial(generate_password_hash, method='pbkdf2:sha256:1'))


@pytest.fixture
def flask_app(tmp_path, monkeypatch):
    mugshot_dir = tmp_path / 'mugshot'
    mugshot_dir.mkdir()
    # croppic 會寫入 / 刪除大頭照，改寫到暫存資料夾，不碰 static/mugshot
    monkeypatch.setattr(chat_app, 'MugShot_FOLDER', str(mugshot_dir))

    app = chat_app.app
    monkeypatch.setitem(app.config, 'TESTING', True)
    # 一般測試不帶 CSRF token；CSRF 本身在 test_csrf.py 測
    monkeypatch.setitem(app.config, 'WTF_CSRF_ENABLED', False)
    with app.app_context():
        db.drop_all()
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def mugshot_dir():
    return chat_app.MugShot_FOLDER


@pytest.fixture
def client(flask_app):
    return flask_app.test_client()


@pytest.fixture
def make_user(flask_app):
    def _make_user(username='alice', password='secret', mugshot='default.jpg'):
        with flask_app.app_context():
            db.session.add(UserAccounts(user_name=username, password=password, mugshot=mugshot))
            db.session.commit()
        return username

    return _make_user


@pytest.fixture
def login(client):
    def _login(username='alice', password='secret'):
        return client.post('/login', data={'username': username, 'password': password})

    return _login


@pytest.fixture
def auth_client(client, make_user, login):
    make_user('alice', 'secret')
    login('alice', 'secret')
    return client


@pytest.fixture
def get_user(flask_app):
    def _get_user(username):
        with flask_app.app_context():
            user = UserAccounts.query.filter_by(UserName=username).first()
            if user is not None:
                db.session.expunge(user)
            return user

    return _get_user


@pytest.fixture
def make_image():
    def _make_image(fmt='PNG', size=(8, 8), color=(255, 0, 0)):
        buf = io.BytesIO()
        Image.new('RGB', size, color).save(buf, format=fmt)
        buf.seek(0)
        return buf

    return _make_image
