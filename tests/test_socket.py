from datetime import datetime

import pytest

import app as chat_app
from dbModel import Message


class FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2024, 5, 6, 7, 8, 9)


@pytest.fixture
def connect(flask_app, make_user):
    """connect('alice') 以 alice 登入後建立 Socket.IO 連線；connect() 是沒登入的連線。"""
    clients = []

    def _connect(username=None, mugshot='default.jpg'):
        http_client = flask_app.test_client()
        if username is not None:
            make_user(username, 'secret', mugshot=mugshot)
            http_client.post('/login', data={'username': username, 'password': 'secret'})
        sc = chat_app.socketio.test_client(flask_app, flask_test_client=http_client)
        clients.append(sc)
        return sc

    yield _connect
    for sc in clients:
        if sc.is_connected():
            sc.disconnect()


def all_messages(app):
    with app.app_context():
        return [(m.UserName, m.Messages) for m in Message.query.all()]


def received_texts(sc):
    return [m['args'][0]['msg'] for m in sc.get_received() if m['name'] == 'getInquiry']


def test_anonymous_connection_is_rejected(connect):
    assert not connect().is_connected()


def test_logged_in_connection_is_accepted(connect):
    assert connect('alice').is_connected()


def test_send_inquiry_saves_and_broadcasts(flask_app, connect, monkeypatch):
    monkeypatch.setattr(chat_app, 'datetime', FrozenDatetime)
    alice = connect('alice', mugshot='alice.png')

    alice.emit('sendInquiry', {'msg': 'hello'})

    assert all_messages(flask_app) == [('alice', 'hello')]
    with flask_app.app_context():
        assert Message.query.one().CreateDate == datetime(2024, 5, 6, 7, 8, 9)
    received = alice.get_received()
    assert len(received) == 1
    assert received[0]['name'] == 'getInquiry'
    data = received[0]['args'][0]
    # 時間是帶時區的 ISO 字串，由前端換成使用者的當地時間
    sent_at = datetime.fromisoformat(data.pop('time'))
    assert sent_at.tzinfo is not None
    assert sent_at == datetime(2024, 5, 6, 7, 8, 9).astimezone()
    assert data == {'Name': 'alice', 'PictureUrl': 'alice.png', 'msg': 'hello'}


def test_every_logged_in_user_receives_messages(connect):
    alice = connect('alice')
    bob = connect('bob')

    alice.emit('sendInquiry', {'msg': 'hi bob'})
    bob.emit('sendInquiry', {'msg': 'hi alice'})

    assert received_texts(alice) == ['hi bob', 'hi alice']
    assert received_texts(bob) == ['hi bob', 'hi alice']


def test_client_supplied_room_is_ignored(connect):
    alice = connect('alice')
    bob = connect('bob')

    alice.emit('sendInquiry', {'msg': 'hello', 'room': 'B_Room'})
    alice.emit('join', {'room': 'B_Room'})

    assert received_texts(bob) == ['hello']


@pytest.mark.parametrize('payload', [
    {'msg': ''},
    {'msg': '   \n '},
    {'msg': 'x' * 1001},
    {'msg': 123},
    {'msg': None},
    {},
    'just a string',
    None,
])
def test_invalid_messages_are_ignored(flask_app, connect, payload):
    alice = connect('alice')
    bob = connect('bob')

    alice.emit('sendInquiry', payload)

    assert all_messages(flask_app) == []
    assert alice.get_received() == []
    assert bob.get_received() == []


def test_message_at_length_limit_is_accepted(flask_app, connect):
    # 上限 1000 字，跟聊天頁輸入框的 maxlength 一致
    alice = connect('alice')
    text = 'x' * 1000

    alice.emit('sendInquiry', {'msg': text})

    assert all_messages(flask_app) == [('alice', text)]
    assert received_texts(alice) == [text]


def test_chat_input_has_same_limit(auth_client):
    html = auth_client.get('/index').get_data(as_text=True)
    assert 'maxlength="1000"' in html


def test_sent_message_shows_up_in_history(flask_app, client, make_user, login):
    make_user('alice', 'secret')
    login('alice', 'secret')
    sender = chat_app.socketio.test_client(flask_app, flask_test_client=client)
    sender.emit('sendInquiry', {'msg': 'persisted'})
    sender.disconnect()

    html = client.get('/index').get_data(as_text=True)

    assert 'persisted' in html
