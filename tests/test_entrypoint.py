import os
import runpy

import flask_socketio

APP_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app.py')


def test_main_starts_socketio_dev_server(monkeypatch):
    calls = []
    monkeypatch.setattr(flask_socketio.SocketIO, 'run', lambda self, app, **kwargs: calls.append(kwargs))

    runpy.run_path(APP_PY, run_name='__main__')

    assert calls == [{'host': '0.0.0.0', 'port': 5000, 'allow_unsafe_werkzeug': True}]
