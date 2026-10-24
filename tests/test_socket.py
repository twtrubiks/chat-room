from datetime import datetime

import pytest

import app as chat_app
from dbModel import Message


class FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2024, 5, 6, 7, 8, 9)


@pytest.fixture
def socket_client(flask_app):
    clients = []

    def _socket_client(flask_client=None):
        sc = chat_app.socketio.test_client(flask_app, flask_test_client=flask_client)
        clients.append(sc)
        return sc

    yield _socket_client
    for sc in clients:
        if sc.is_connected():
            sc.disconnect()


def all_messages(app):
    with app.app_context():
        return [(m.UserName, m.Messages) for m in Message.query.all()]


def test_connect(socket_client):
    assert socket_client().is_connected()


def test_send_inquiry_saves_and_broadcasts_to_room(flask_app, client, make_user, login, socket_client,
                                                   monkeypatch):
    monkeypatch.setattr(chat_app, 'datetime', FrozenDatetime)
    make_user('alice', 'secret', mugshot='alice.png')
    login('alice', 'secret')
    sender = socket_client(client)
    sender.emit('join', {'room': 'A_Room'})

    sender.emit('sendInquiry', {'msg': 'hello', 'room': 'A_Room'})

    assert all_messages(flask_app) == [('alice', 'hello')]
    with flask_app.app_context():
        assert Message.query.one().CreateDate == datetime(2024, 5, 6, 7, 8, 9)
    received = sender.get_received()
    assert len(received) == 1
    assert received[0]['name'] == 'getInquiry'
    assert received[0]['args'][0] == {
        'time': '2024-05-06 07:08',
        'Name': 'alice',
        'PictureUrl': 'alice.png',
        'msg': 'hello',
    }


def test_broadcast_only_reaches_joined_room(client, make_user, login, socket_client):
    make_user('alice', 'secret')
    login('alice', 'secret')
    sender = socket_client(client)
    same_room = socket_client()
    other_room = socket_client()
    not_joined = socket_client()
    sender.emit('join', {'room': 'A_Room'})
    same_room.emit('join', {'room': 'A_Room'})
    other_room.emit('join', {'room': 'B_Room'})

    sender.emit('sendInquiry', {'msg': 'hello', 'room': 'A_Room'})

    assert [m['args'][0]['msg'] for m in same_room.get_received()] == ['hello']
    assert other_room.get_received() == []
    assert not_joined.get_received() == []


def test_anonymous_send_is_ignored(flask_app, socket_client):
    anonymous = socket_client()
    anonymous.emit('join', {'room': 'A_Room'})

    anonymous.emit('sendInquiry', {'msg': 'spam', 'room': 'A_Room'})

    assert all_messages(flask_app) == []
    assert anonymous.get_received() == []


def test_sent_message_shows_up_in_history(flask_app, client, make_user, login, socket_client):
    make_user('alice', 'secret')
    login('alice', 'secret')
    sender = socket_client(client)
    sender.emit('join', {'room': 'A_Room'})
    sender.emit('sendInquiry', {'msg': 'persisted', 'room': 'A_Room'})

    html = client.get('/index').get_data(as_text=True)

    assert 'persisted' in html
