import os
import runpy

APP_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app.py')


def load_app_module():
    return runpy.run_path(APP_PY, run_name='app_under_test')


def test_secret_key_from_env(monkeypatch):
    monkeypatch.setenv('SECRET_KEY', 'from-env')
    assert load_app_module()['app'].secret_key == 'from-env'


def test_secret_key_is_random_when_not_configured(monkeypatch):
    monkeypatch.delenv('SECRET_KEY', raising=False)

    first = load_app_module()['app'].secret_key
    second = load_app_module()['app'].secret_key

    assert first != second
    # 至少 32 bytes 的亂數（hex 編碼後 64 個字元）
    assert len(first) >= 64
    assert len(second) >= 64
