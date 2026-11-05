import re
from datetime import datetime

import pytest

from dbModel import Message, db

MESSAGE_RE = re.compile(
    r'<div class="message new">\s*'
    r'<figure class="avatar"><img src="static/mugshot/(?P<mugshot>[^"]*)" alt="(?P<user>[^"]*)"[^>]*></figure>\s*'
    r'(?P<text>.*?)\s*'
    r'<div class="timestamp"><time datetime="(?P<iso>[^"]*)">(?P<time>[^<]*)</time></div>',
    re.S,
)


def rendered_messages(html):
    return [m.group('mugshot', 'user', 'text', 'time') for m in MESSAGE_RE.finditer(html)]


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

    def test_login_page_shows_login_message(self, client):
        html = client.get('/index', follow_redirects=True).get_data(as_text=True)

        assert '<div class="alert alert-info" role="alert">Please LOG IN</div>' in html
        # 顯示過一次就清掉
        assert 'Please LOG IN' not in client.get('/login').get_data(as_text=True)

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

        assert rendered_messages(html) == [
            ('alice.png', 'alice', 'hello from alice', '2024-01-01 09:05'),
            ('bob.png', 'bob', 'hi from bob', '2024-01-01 13:45'),
            ('alice.png', 'alice', 'bye', '2024-01-02 23:59'),
        ]

    def test_history_is_in_chronological_order(self, flask_app, auth_client):
        add_message(flask_app, 'alice', 'third', datetime(2024, 1, 2, 8, 0))
        add_message(flask_app, 'alice', 'first', datetime(2024, 1, 1, 9, 0))
        add_message(flask_app, 'alice', 'second', datetime(2024, 1, 1, 10, 0))
        # 同一時間的訊息依寫入順序
        add_message(flask_app, 'alice', 'fourth', datetime(2024, 1, 3, 7, 0))
        add_message(flask_app, 'alice', 'fifth', datetime(2024, 1, 3, 7, 0))

        html = auth_client.get('/index').get_data(as_text=True)

        assert [text for _, _, text, _ in rendered_messages(html)] == ['first', 'second', 'third', 'fourth', 'fifth']

    def test_timestamps_carry_timezone_for_the_browser(self, flask_app, auth_client):
        created = datetime(2024, 1, 1, 9, 5, 30, 123456)
        add_message(flask_app, 'alice', 'hello', created)

        html = auth_client.get('/index').get_data(as_text=True)

        iso = MESSAGE_RE.search(html).group('iso')
        # DB 存的是伺服器當地時間，送給瀏覽器時要帶上時區（精確到秒）
        assert datetime.fromisoformat(iso) == created.replace(microsecond=0).astimezone()
        assert datetime.fromisoformat(iso).tzinfo is not None
        assert re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}', iso)

    def test_messages_without_account_are_skipped(self, flask_app, auth_client):
        add_message(flask_app, 'ghost', 'orphan message', datetime(2024, 1, 1, 9, 5))
        add_message(flask_app, 'alice', 'real message', datetime(2024, 1, 1, 9, 6))

        html = auth_client.get('/index').get_data(as_text=True)

        assert rendered_messages(html) == [('default.jpg', 'alice', 'real message', '2024-01-01 09:06')]

    def test_message_html_is_escaped(self, flask_app, auth_client):
        add_message(flask_app, 'alice', '<script>alert(1)</script>', datetime(2024, 1, 1, 9, 5))

        html = auth_client.get('/index').get_data(as_text=True)

        assert '<script>alert(1)</script>' not in html
        assert '&lt;script&gt;alert(1)&lt;/script&gt;' in html
