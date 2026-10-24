import threading
import time

import pytest
from werkzeug.serving import make_server

sync_api = pytest.importorskip('playwright.sync_api')

import app as chat_app  # noqa: E402

ROOM = 'A_Room'


@pytest.fixture(scope='session')
def live_server():
    server = make_server('127.0.0.1', 0, chat_app.app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield 'http://127.0.0.1:{}'.format(server.server_port)
    server.shutdown()
    thread.join()


@pytest.fixture(scope='session')
def browser():
    with sync_api.sync_playwright() as p:
        browser = p.chromium.launch()
        yield browser
        browser.close()


@pytest.fixture(autouse=True)
def e2e_app(flask_app, monkeypatch):
    # 瀏覽器測試要連 JS 送出的 CSRF token 一起驗證
    monkeypatch.setitem(flask_app.config, 'WTF_CSRF_ENABLED', True)
    return flask_app


def room_size():
    return len(list(chat_app.socketio.server.manager.get_participants('/', ROOM)))


def wait_until(predicate, timeout=10.0, message='condition'):
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() > deadline:
            raise AssertionError('timed out waiting for ' + message)
        time.sleep(0.05)


@pytest.fixture
def wait_for_room():
    def _wait_for_room(members):
        wait_until(lambda: room_size() == members, message='{} member(s) in {}'.format(members, ROOM))

    return _wait_for_room


@pytest.fixture
def new_page(browser, live_server):
    """每次呼叫開一個獨立的 browser context（等於另一個使用者）。"""
    contexts = []
    errors = []

    def _new_page():
        context = browser.new_context(base_url=live_server)
        context.set_default_timeout(10000)
        page = context.new_page()
        page.on('pageerror', lambda exc: errors.append('pageerror: {}'.format(exc)))
        page.on('dialog', lambda dialog: (errors.append('dialog: {}'.format(dialog.message)), dialog.dismiss()))
        contexts.append(context)
        return page

    yield _new_page
    for context in contexts:
        context.close()
    # 關掉的分頁可能要等 ping timeout 才會被伺服器判定斷線，直接清掉，避免影響下一個測試的 room 人數
    for sid, _ in list(chat_app.socketio.server.manager.get_participants('/', ROOM)):
        chat_app.socketio.server.disconnect(sid, namespace='/')
    assert room_size() == 0
    assert errors == []


@pytest.fixture
def login_page(new_page, make_user):
    def _login_page(username, password='secret', mugshot='default.jpg'):
        make_user(username, password, mugshot=mugshot)
        page = new_page()
        page.goto('/login')
        page.fill('#username', username)
        page.fill('#password', password)
        page.click('button[type=submit]')
        page.wait_for_url('**/index')
        return page

    return _login_page
