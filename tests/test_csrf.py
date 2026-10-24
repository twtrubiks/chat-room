import re
import time

import pytest


@pytest.fixture
def csrf_client(flask_app, client, monkeypatch):
    monkeypatch.setitem(flask_app.config, 'WTF_CSRF_ENABLED', True)
    return client


def csrf_token(client, path='/login'):
    html = client.get(path).get_data(as_text=True)
    return re.search(r'<meta name="csrf-token" content="([^"]+)">', html).group(1)


@pytest.mark.parametrize('path', ['/login', '/register'])
def test_forms_include_token(csrf_client, path):
    html = csrf_client.get(path).get_data(as_text=True)
    form_token = re.search(r'<input type="hidden" name="csrf_token" value="([^"]+)">', html).group(1)
    assert form_token == re.search(r'<meta name="csrf-token" content="([^"]+)">', html).group(1)


def test_login_requires_token(csrf_client, make_user):
    make_user('alice', 'secret')

    resp = csrf_client.post('/login', data={'username': 'alice', 'password': 'secret'})

    assert resp.status_code == 400
    with csrf_client.session_transaction() as sess:
        assert '_user_id' not in sess


def test_login_with_token(csrf_client, make_user):
    make_user('alice', 'secret')
    token = csrf_token(csrf_client)

    resp = csrf_client.post('/login', data={'username': 'alice', 'password': 'secret', 'csrf_token': token})

    assert resp.status_code == 302
    assert resp.headers['Location'] == '/index'


def test_register_requires_token(csrf_client, get_user):
    resp = csrf_client.post('/register', data={'username': 'bob', 'password': 'pw123'})

    assert resp.status_code == 400
    assert get_user('bob') is None


def test_register_with_token(csrf_client, get_user):
    token = csrf_token(csrf_client, '/register')

    resp = csrf_client.post('/register', data={'username': 'bob', 'password': 'pw123', 'csrf_token': token})

    assert resp.status_code == 302
    assert get_user('bob') is not None


def test_check_username_api_requires_header(csrf_client):
    token = csrf_token(csrf_client, '/register')

    assert csrf_client.post('/API_check_UserNameExist', data={'username': 'bob'}).status_code == 400
    resp = csrf_client.post('/API_check_UserNameExist', data={'username': 'bob'}, headers={'X-CSRFToken': token})
    assert resp.get_json() is True


def test_croppic_requires_header(csrf_client, make_user, make_image, get_user):
    make_user('alice', 'secret')
    token = csrf_token(csrf_client)
    csrf_client.post('/login', data={'username': 'alice', 'password': 'secret', 'csrf_token': token})

    resp = csrf_client.post('/croppic', data={'image': (make_image(), 'a.png')}, content_type='multipart/form-data')
    assert resp.status_code == 400
    assert get_user('alice').MugShot == 'default.jpg'

    resp = csrf_client.post('/croppic', data={'image': (make_image(), 'a.png')}, content_type='multipart/form-data',
                            headers={'X-CSRFToken': token})
    assert resp.get_json()['status'] == 'success'


def test_logout_requires_token(csrf_client, make_user):
    make_user('alice', 'secret')
    token = csrf_token(csrf_client)
    csrf_client.post('/login', data={'username': 'alice', 'password': 'secret', 'csrf_token': token})

    assert csrf_client.post('/logout').status_code == 400
    with csrf_client.session_transaction() as sess:
        assert sess['_user_id'] == 'alice'

    html = csrf_client.get('/index').get_data(as_text=True)
    form_token = re.search(r'<form class="logout-form".*?name="csrf_token" value="([^"]+)"', html, re.S).group(1)
    assert csrf_client.post('/logout', data={'csrf_token': form_token}).status_code == 302
    with csrf_client.session_transaction() as sess:
        assert '_user_id' not in sess


def test_token_does_not_expire_while_session_lives(csrf_client, monkeypatch):
    # 聊天頁可能開好幾個小時才上傳大頭照，token 不能一小時就過期（Flask-WTF 預設 3600 秒）
    token = csrf_token(csrf_client, '/register')
    now = time.time()
    monkeypatch.setattr(time, 'time', lambda: now + 24 * 3600)

    resp = csrf_client.post('/API_check_UserNameExist', data={'username': 'bob'}, headers={'X-CSRFToken': token})

    assert resp.status_code == 200


def test_socketio_rejects_cross_origin(client):
    # CSRFProtect 不管 WebSocket；Socket.IO 靠 engineio 預設的同源檢查擋跨站連線
    path = '/socket.io/?EIO=4&transport=polling'
    assert client.get(path, headers={'Origin': 'http://evil.example'}).status_code == 400
    assert client.get(path, headers={'Origin': 'http://localhost'}).status_code == 200
