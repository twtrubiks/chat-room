import hashlib

import pytest

import app as chat_app
from dbModel import UserAccounts, db


def md5(s):
    return hashlib.md5(s.encode('utf-8')).hexdigest()


def set_password_column(app, username, value):
    with app.app_context():
        UserAccounts.query.filter_by(UserName=username).first().Password = value
        db.session.commit()


class TestQueryUser:
    def test_existing_user(self, flask_app, make_user):
        make_user('alice')
        with flask_app.app_context():
            assert chat_app.query_user('alice') is True

    def test_missing_user(self, flask_app):
        with flask_app.app_context():
            assert chat_app.query_user('nobody') is False


class TestUserLoader:
    def test_loads_existing_user(self, flask_app, make_user):
        make_user('alice')
        with flask_app.app_context():
            user = chat_app.user_loader('alice')
        assert isinstance(user, chat_app.User)
        assert user.id == 'alice'

    def test_missing_user_returns_none(self, flask_app):
        with flask_app.app_context():
            assert chat_app.user_loader('nobody') is None


class TestLogin:
    def test_get_renders_form(self, client):
        resp = client.get('/login')
        assert resp.status_code == 200
        assert b'name="username"' in resp.data
        assert b'name="password"' in resp.data
        assert b'username or password error' not in resp.data

    def test_head(self, client):
        assert client.head('/login').status_code == 200

    def test_get_when_logged_in_redirects_to_index(self, auth_client):
        resp = auth_client.get('/login')
        assert resp.status_code == 302
        assert resp.headers['Location'] == '/index'

    def test_success(self, client, make_user, login):
        make_user('alice', 'secret')
        resp = login('alice', 'secret')

        assert resp.status_code == 302
        assert resp.headers['Location'] == '/index'
        with client.session_transaction() as sess:
            assert sess['_user_id'] == 'alice'
            assert ('message', 'Logged in successfully') in sess['_flashes']
        # login_user(remember=True) 會發 remember cookie
        assert client.get_cookie('remember_token') is not None

    def test_unknown_user(self, client, login):
        resp = login('nobody', 'secret')
        assert resp.status_code == 200
        assert b'username or password error' in resp.data
        with client.session_transaction() as sess:
            assert '_user_id' not in sess

    @pytest.mark.parametrize('wrong', ['wrong', ''])
    def test_wrong_password(self, client, make_user, login, wrong):
        make_user('alice', 'secret')
        resp = login('alice', wrong)

        assert resp.status_code == 200
        assert b'username or password error' in resp.data
        with client.session_transaction() as sess:
            assert '_user_id' not in sess

    def test_account_without_password_cannot_login_with_empty_password(self, flask_app, client, make_user,
                                                                      login):
        # 舊版允許空密碼註冊，DB 裡存的是 NULL
        make_user('alice', 'secret')
        set_password_column(flask_app, 'alice', None)

        resp = login('alice', '')

        assert b'username or password error' in resp.data
        with client.session_transaction() as sess:
            assert '_user_id' not in sess

    def test_login_keeps_modern_hash(self, client, make_user, login, get_user):
        make_user('alice', 'secret')
        before = get_user('alice').Password

        login('alice', 'secret')

        assert get_user('alice').Password == before

    def test_legacy_md5_account_is_upgraded_on_login(self, flask_app, client, make_user, login, get_user):
        make_user('alice', 'secret')
        set_password_column(flask_app, 'alice', md5('secret'))

        resp = login('alice', 'secret')

        assert resp.headers['Location'] == '/index'
        user = get_user('alice')
        assert not user.is_legacy_hash()
        assert user.check_password('secret')

    def test_legacy_md5_account_wrong_password_is_not_upgraded(self, flask_app, client, make_user, login,
                                                               get_user):
        make_user('alice', 'secret')
        set_password_column(flask_app, 'alice', md5('secret'))

        resp = login('alice', 'wrong')

        assert b'username or password error' in resp.data
        assert get_user('alice').Password == md5('secret')


class TestRegister:
    def test_get_renders_form(self, client):
        resp = client.get('/register')
        assert resp.status_code == 200
        assert b'name="username"' in resp.data
        # GET 不能被當成送出空表單
        assert b'username and password are required' not in resp.data

    def test_head(self, client):
        assert client.head('/register').status_code == 200

    def test_creates_account(self, client, get_user):
        resp = client.post('/register', data={'username': 'bob', 'password': 'pw123'})

        assert resp.status_code == 302
        assert resp.headers['Location'] == '/index'
        user = get_user('bob')
        assert user is not None
        assert user.check_password('pw123')
        assert user.MugShot == 'default.jpg'

    def test_registration_logs_user_in(self, client):
        client.post('/register', data={'username': 'bob', 'password': 'pw123'})

        with client.session_transaction() as sess:
            assert sess['_user_id'] == 'bob'
        assert client.get_cookie('remember_token') is not None
        assert '<h1>bob</h1>' in client.get('/index').get_data(as_text=True)

    def test_registered_user_can_login_again(self, client, login):
        client.post('/register', data={'username': 'bob', 'password': 'pw123'})
        client.get('/logout')

        resp = login('bob', 'pw123')

        assert resp.headers['Location'] == '/index'
        with client.session_transaction() as sess:
            assert sess['_user_id'] == 'bob'

    def test_failed_registration_does_not_log_in(self, client, make_user):
        make_user('alice', 'secret')
        client.post('/register', data={'username': 'alice', 'password': 'other'})

        with client.session_transaction() as sess:
            assert '_user_id' not in sess

    def test_username_is_trimmed(self, client, get_user):
        client.post('/register', data={'username': '  bob  ', 'password': 'pw123'})

        assert get_user('bob') is not None
        assert get_user('  bob  ') is None
        with client.session_transaction() as sess:
            assert sess['_user_id'] == 'bob'

    def test_trimmed_duplicate_is_rejected(self, client, make_user):
        make_user('alice', 'secret')

        resp = client.post('/register', data={'username': ' alice ', 'password': 'other'})

        assert b'UserName already exists.' in resp.data

    def test_duplicate_username(self, client, make_user, get_user):
        make_user('alice', 'secret')
        before = get_user('alice').Password

        resp = client.post('/register', data={'username': 'alice', 'password': 'other'})

        assert resp.status_code == 200
        assert b'UserName already exists.' in resp.data
        assert get_user('alice').Password == before

    def test_can_register_again_after_duplicate(self, client, make_user, get_user):
        make_user('alice', 'secret')
        client.post('/register', data={'username': 'alice', 'password': 'other'})

        resp = client.post('/register', data={'username': 'bob', 'password': 'pw123'})

        assert resp.headers['Location'] == '/index'
        assert get_user('bob') is not None

    @pytest.mark.parametrize('data', [
        {'username': 'bob', 'password': ''},
        {'username': '', 'password': 'pw123'},
        {'username': '   ', 'password': 'pw123'},
        {'username': 'bob'},
        {'password': 'pw123'},
        {},
    ])
    def test_username_and_password_required(self, client, get_user, data):
        resp = client.post('/register', data=data)

        assert resp.status_code == 200
        assert b'username and password are required' in resp.data
        assert get_user('bob') is None
        assert get_user('') is None
        assert get_user('   ') is None


class TestLogout:
    def test_logout_clears_session(self, auth_client):
        resp = auth_client.get('/logout')

        assert resp.status_code == 302
        assert resp.headers['Location'] == '/index'
        with auth_client.session_transaction() as sess:
            assert '_user_id' not in sess
        assert auth_client.get('/index').status_code == 302


class TestCheckUserNameExist:
    """API 回傳 True 代表「名稱可以用（不存在）」。"""

    def test_form_new_name(self, client):
        resp = client.post('/API_check_UserNameExist', data={'username': 'bob'})
        assert resp.get_json() is True

    def test_form_existing_name(self, client, make_user):
        make_user('alice')
        resp = client.post('/API_check_UserNameExist', data={'username': 'alice'})
        assert resp.get_json() is False

    def test_json_new_name(self, client):
        resp = client.post('/API_check_UserNameExist', json={'username': 'bob'})
        assert resp.get_json() is True

    def test_json_existing_name(self, client, make_user):
        make_user('alice')
        resp = client.post('/API_check_UserNameExist', json={'username': 'alice'})
        assert resp.get_json() is False

    def test_name_is_trimmed_like_register(self, client, make_user):
        make_user('alice')
        assert client.post('/API_check_UserNameExist', data={'username': ' alice '}).get_json() is False
        assert client.post('/API_check_UserNameExist', json={'username': ' alice '}).get_json() is False

    @pytest.mark.parametrize('kwargs', [
        {},
        {'data': {'username': ''}},
        {'data': {'username': '   '}},
        {'json': {}},
        {'json': {'username': ''}},
        {'json': {'username': 123}},
        {'json': {'username': ['alice']}},
    ])
    def test_missing_username(self, client, kwargs):
        resp = client.post('/API_check_UserNameExist', **kwargs)
        assert resp.status_code == 200
        assert resp.get_json() is False

    def test_get_not_allowed(self, client):
        assert client.get('/API_check_UserNameExist').status_code == 405
