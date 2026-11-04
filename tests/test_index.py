import re
from datetime import datetime

import pytest

from dbModel import Message, db

MESSAGE_RE = re.compile(
    r'<div class="message new">\s*'
    r'<figure class="avatar"><img src="static/mugshot/(?P<mugshot>[^"]*)" alt="(?P<user>[^"]*)"[^>]*></figure>\s*'
    r'(?P<text>.*?)\s*'
    r'<div class="timestamp">(?P<time>[^<]*)</div>',
    re.S,
)


def rendered_messages(html):
    return sorted(m.group('mugshot', 'user', 'text', 'time') for m in MESSAGE_RE.finditer(html))


def add_message(app, username, text, created):
    with app.app_context():
        db.session.add(Message(username, text, created))
        db.session.commit()


class TestLoginRequired:
    @pytest.mark.parametrize('path', ['/', '/index'])
    def test_anonymous_redirected_to_login(self, client, path):
        resp = client.get(path)

        assert resp.status_code == 302
        assert resp.headers['Location'].startswith('/login?next=')
        with client.session_transaction() as sess:
            assert ('info', 'Please LOG IN') in sess['_flashes']

    @pytest.mark.parametrize('path', ['/', '/index'])
    def test_logged_in_user_sees_chat(self, auth_client, path):
        resp = auth_client.get(path)
        assert resp.status_code == 200
        assert b'class="message-input"' in resp.data

    @pytest.mark.parametrize('path', ['/', '/index'])
    def test_post_not_allowed(self, auth_client, path):
        assert auth_client.post(path).status_code == 405


class TestIndexContent:
    def test_header_shows_current_user_and_mugshot(self, client, make_user, login):
        make_user('alice', 'secret', mugshot='alice.png')
        make_user('bob', 'secret', mugshot='bob.png')
        login('alice', 'secret')

        html = client.get('/index').get_data(as_text=True)

        assert '<h1>alice</h1>' in html
        assert '<img src="static/mugshot/alice.png" />' in html

    def test_no_messages(self, auth_client):
        html = auth_client.get('/index').get_data(as_text=True)
        assert rendered_messages(html) == []

    def test_lists_history_with_each_authors_mugshot(self, flask_app, client, make_user, login):
        make_user('alice', 'secret', mugshot='alice.png')
        make_user('bob', 'secret', mugshot='bob.png')
        add_message(flask_app, 'alice', 'hello from alice', datetime(2024, 1, 1, 9, 5))
        add_message(flask_app, 'bob', 'hi from bob', datetime(2024, 1, 1, 13, 45))
        add_message(flask_app, 'alice', 'bye', datetime(2024, 1, 2, 23, 59))
        login('alice', 'secret')

        html = client.get('/index').get_data(as_text=True)

        assert rendered_messages(html) == sorted([
            ('alice.png', 'alice', 'hello from alice', '09:05'),
            ('bob.png', 'bob', 'hi from bob', '13:45'),
            ('alice.png', 'alice', 'bye', '23:59'),
        ])

    def test_messages_without_account_are_skipped(self, flask_app, auth_client):
        add_message(flask_app, 'ghost', 'orphan message', datetime(2024, 1, 1, 9, 5))
        add_message(flask_app, 'alice', 'real message', datetime(2024, 1, 1, 9, 6))

        html = auth_client.get('/index').get_data(as_text=True)

        assert rendered_messages(html) == [('default.jpg', 'alice', 'real message', '09:06')]

    def test_message_html_is_escaped(self, flask_app, auth_client):
        add_message(flask_app, 'alice', '<script>alert(1)</script>', datetime(2024, 1, 1, 9, 5))

        html = auth_client.get('/index').get_data(as_text=True)

        assert '<script>alert(1)</script>' not in html
        assert '&lt;script&gt;alert(1)&lt;/script&gt;' in html
