import hashlib

import pytest

import app as chat_app


def md5(s):
    return hashlib.md5(s.encode('utf-8')).hexdigest()


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

    # 同時涵蓋「錯誤密碼的雜湊值比正確的小 / 大」兩種情況，
    # 這樣把 == 換成 <=、>= 之類的比較運算子也會被抓到。
    @pytest.mark.parametrize('wrong', ['wrong', 'badpass'])
    def test_wrong_password(self, client, make_user, login, wrong):
        assert md5(wrong) != md5('secret')
        make_user('alice', 'secret')
        resp = login('alice', wrong)

        assert resp.status_code == 200
        assert b'username or password error' in resp.data
        with client.session_transaction() as sess:
            assert '_user_id' not in sess

    def test_wrong_password_hashes_cover_both_orderings(self):
        assert md5('wrong') < md5('secret') < md5('badpass')


class TestRegister:
    def test_get_renders_form(self, client):
        resp = client.get('/register')
        assert resp.status_code == 200
        assert b'name="username"' in resp.data

    def test_creates_account(self, client, get_user):
        resp = client.post('/register', data={'username': 'bob', 'password': 'pw123'})

        assert resp.status_code == 302
        assert resp.headers['Location'] == '/index'
        user = get_user('bob')
        assert user is not None
        assert user.Password == md5('pw123')
        assert user.MugShot == 'default.jpg'

    def test_registered_user_can_login(self, client, login):
        client.post('/register', data={'username': 'bob', 'password': 'pw123'})
        resp = login('bob', 'pw123')
        assert resp.headers['Location'] == '/index'


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

    @pytest.mark.parametrize('kwargs', [
        {},
        {'data': {'username': ''}},
        {'json': {}},
        {'json': {'username': ''}},
    ])
    def test_missing_username(self, client, kwargs):
        resp = client.post('/API_check_UserNameExist', **kwargs)
        assert resp.status_code == 200
        assert resp.get_json() is False

    def test_get_not_allowed(self, client):
        assert client.get('/API_check_UserNameExist').status_code == 405
