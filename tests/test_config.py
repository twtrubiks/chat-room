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


def test_platform_database_url_is_ignored(monkeypatch):
    # Heroku 等平台會自動設定 DATABASE_URL，而且是 SQLAlchemy 不接受的 postgres:// 格式
    monkeypatch.setenv('DATABASE_URL', 'postgres://user:pw@db.example.com/prod')
    uri = load_app_module()['app'].config['SQLALCHEMY_DATABASE_URI']
    assert uri == os.environ['CHAT_ROOM_DATABASE_URL']


def test_database_uri_from_env(monkeypatch, tmp_path):
    uri = 'sqlite:///' + str(tmp_path / 'other.db')
    monkeypatch.setenv('CHAT_ROOM_DATABASE_URL', uri)
    assert load_app_module()['app'].config['SQLALCHEMY_DATABASE_URI'] == uri


def test_database_uri_default(monkeypatch, tmp_path):
    monkeypatch.delenv('CHAT_ROOM_DATABASE_URL')
    monkeypatch.delenv('DATABASE_URL', raising=False)
    # 預設的相對 SQLite 路徑會建立 instance/ 資料夾，切到暫存目錄避免弄髒專案
    monkeypatch.chdir(tmp_path)
    assert load_app_module()['app'].config['SQLALCHEMY_DATABASE_URI'] == 'sqlite:///app.db'
