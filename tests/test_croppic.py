import io
import os
import re

import pytest
from werkzeug.datastructures import FileStorage
from werkzeug.test import encode_multipart

from dbModel import UserAccounts, db

UUID_NAME = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'


def upload(client, data, filename='avatar.png'):
    return client.post('/croppic', data={'image': (data, filename)}, content_type='multipart/form-data')


def set_mugshot(app, username, mugshot):
    with app.app_context():
        UserAccounts.query.filter_by(UserName=username).first().MugShot = mugshot
        db.session.commit()


def test_requires_login(client, make_image):
    resp = upload(client, make_image())
    assert resp.status_code == 302
    assert resp.headers['Location'].startswith('/login?next=')


def test_missing_image(auth_client):
    resp = auth_client.post('/croppic', data={}, content_type='multipart/form-data')
    assert resp.status_code == 400
    assert resp.get_json() == {'status': 'error', 'message': 'no image'}


def test_invalid_image(auth_client, get_user, mugshot_dir):
    resp = upload(auth_client, io.BytesIO(b'definitely not an image'))

    assert resp.status_code == 500
    assert resp.get_json()['status'] == 'error'
    assert resp.get_json()['message']
    assert get_user('alice').MugShot == 'default.jpg'
    assert os.listdir(mugshot_dir) == []


@pytest.mark.parametrize('fmt, ext', [('PNG', 'png'), ('JPEG', 'jpeg'), ('GIF', 'gif')])
def test_upload_saves_file_and_updates_user(auth_client, get_user, mugshot_dir, make_image, fmt, ext):
    resp = upload(auth_client, make_image(fmt))

    assert resp.status_code == 200
    body = resp.get_json()
    assert body['status'] == 'success'
    assert re.fullmatch(UUID_NAME + r'\.' + ext, body['filename'])
    assert body['url'] == '/static/mugshot/' + body['filename']
    assert get_user('alice').MugShot == body['filename']
    assert os.listdir(mugshot_dir) == [body['filename']]


def test_default_mugshot_is_never_deleted(auth_client, mugshot_dir, make_image):
    default = os.path.join(mugshot_dir, 'default.jpg')
    open(default, 'wb').close()

    resp = upload(auth_client, make_image())

    assert resp.status_code == 200
    assert os.path.exists(default)


# 舊檔名同時涵蓋比 'default.jpg' 小與大的字串，
# 這樣把 != 換成 <、> 之類的比較運算子也會被抓到。
@pytest.mark.parametrize('old_name', [
    '02fe516c-3c91-11e7-b43b-4ccc6a2a56fa.jpeg',
    'f2fe516c-3c91-11e7-b43b-4ccc6a2a56fa.png',
])
def test_replacing_custom_mugshot_deletes_old_file(flask_app, auth_client, get_user, mugshot_dir, make_image,
                                                   old_name):
    assert old_name != 'default.jpg'
    set_mugshot(flask_app, 'alice', old_name)
    open(os.path.join(mugshot_dir, old_name), 'wb').close()

    resp = upload(auth_client, make_image())

    assert resp.status_code == 200
    new_name = resp.get_json()['filename']
    assert get_user('alice').MugShot == new_name
    assert os.listdir(mugshot_dir) == [new_name]


def test_old_mugshot_file_already_gone(flask_app, auth_client, get_user, mugshot_dir, make_image):
    set_mugshot(flask_app, 'alice', 'missing.png')

    resp = upload(auth_client, make_image())

    assert resp.status_code == 200
    assert get_user('alice').MugShot == resp.get_json()['filename']


@pytest.mark.parametrize('size', [(1024, 1024), (1024, 1), (1, 1024)])
def test_image_at_max_dimensions_is_accepted(auth_client, make_image, size):
    resp = upload(auth_client, make_image(size=size))
    assert resp.get_json()['status'] == 'success'


@pytest.mark.parametrize('size', [(1025, 10), (10, 1025)])
def test_oversized_image_is_rejected(auth_client, get_user, mugshot_dir, make_image, size):
    resp = upload(auth_client, make_image(size=size))

    assert resp.status_code == 400
    assert resp.get_json() == {'status': 'error', 'message': 'image too large'}
    assert get_user('alice').MugShot == 'default.jpg'
    assert os.listdir(mugshot_dir) == []


def multipart_body(total_size):
    """產生整個 request body 剛好 total_size bytes 的 multipart 上傳。"""
    def encode(payload):
        image = FileStorage(stream=io.BytesIO(payload), filename='a.png', content_type='image/png')
        return encode_multipart({'image': image}, boundary='test-boundary')

    _, one_byte = encode(b'x')
    boundary, body = encode(b'x' * (total_size - len(one_byte) + 1))
    assert len(body) == total_size
    return body, 'multipart/form-data; boundary=' + boundary


# 上傳上限 2 MB（整個 request body）
@pytest.mark.parametrize('total_size, too_large', [
    (2 * 1024 * 1024, False),
    (2 * 1024 * 1024 + 1, True),
])
def test_request_size_limit(auth_client, total_size, too_large):
    body, content_type = multipart_body(total_size)

    resp = auth_client.post('/croppic', data=body, content_type=content_type)

    if too_large:
        assert resp.status_code == 413
        assert resp.get_json() == {'status': 'error', 'message': 'file too large'}
    else:
        # 沒超過上限就會進到圖片檢查（內容不是圖片，所以是 500）
        assert resp.status_code == 500
        assert resp.get_json()['message'] != 'file too large'
