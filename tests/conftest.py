import io
import os
import tempfile

import pytest
from PIL import Image

# app.py 在 import 時就會用 SQLALCHEMY_DATABASE_URI 建立 engine，
# 所以必須在 import app 之前把 DB 指到暫存檔，避免動到專案裡的 app.db。
_DB_DIR = tempfile.mkdtemp(prefix='chat-room-test-')
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(_DB_DIR, 'test.db')

import app as chat_app  # noqa: E402
from dbModel import UserAccounts, db  # noqa: E402


@pytest.fixture
def flask_app(tmp_path, monkeypatch):
    mugshot_dir = tmp_path / 'mugshot'
    mugshot_dir.mkdir()
    # croppic 會寫入 / 刪除大頭照，改寫到暫存資料夾，不碰 static/mugshot
    monkeypatch.setattr(chat_app, 'MugShot_FOLDER', str(mugshot_dir))

    app = chat_app.app
    app.config.update(TESTING=True)
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
