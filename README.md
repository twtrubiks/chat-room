# chat-room

Chat-Room Use Python Socket.IO

* [Youtube Demo](https://youtu.be/l53-K03hIXs)

聊天室,相信大家一定經常看到,今天教你使用 [python-socketio](https://github.com/miguelgrinberg/python-socketio) 打造一個簡易的聊天室。

使用 Python [Flask](https://flask.palletsprojects.com/) 搭配 [python-socketio](https://github.com/miguelgrinberg/python-socketio) 建立聊天室,資料庫使用 SQLite。

## 特色

* [Flask-SocketIO](https://flask-socketio.readthedocs.io/) 即時聊天室
* 透過 [Flask-Login](https://flask-login.readthedocs.io/) 實現簡易登入、註冊
* 使用 [Cropper.js](https://github.com/fengyuanchen/cropperjs/) 上傳並裁切大頭照
* 前端 [Bootstrap 5](https://getbootstrap.com/) + [Font Awesome 6](https://fontawesome.com/),聊天頁無 jQuery 依賴

## 安裝套件

確定電腦有安裝 [Python](https://www.python.org/) 之後

請在  cmd (命令提示字元) 輸入以下指令

``` cmd
pip install -r requirements.txt
```

## 資料庫初始化

設定 Flask app 後執行 migration:

```cmd
export FLASK_APP=app.py
flask db upgrade
```

預設使用 SQLite(`instance/app.db`)。要換資料庫請設定 `CHAT_ROOM_DATABASE_URL`,例如 `postgresql://user:password@localhost/db`(需另外安裝對應的 driver)。

## 啟動

```cmd
python app.py
```

預設會在 `http://localhost:5000` 啟動，使用 Flask-SocketIO 內建的開發伺服器。

## 測試

```cmd
pip install -r requirements-dev.txt
playwright install chromium
pytest
```

測試會透過 `CHAT_ROOM_DATABASE_URL` 改用暫存的 SQLite,大頭照也寫到暫存資料夾,不會動到 `instance/app.db` 與 `static/mugshot`。

`tests/e2e/` 是用 [Playwright](https://playwright.dev/python/) 開真的瀏覽器測前端 JS(登入、註冊檢查、聊天、上傳大頭照)。頁面會從 CDN 載入 Bootstrap、Socket.IO、Cropper.js,所以需要網路;只想跑後端測試可以用 `pytest --ignore=tests/e2e`。

GitHub Actions(`.github/workflows/tests.yml`)會在每次 push 與 PR 自動跑全部測試。

### 變異測試 (Mutation Testing)

使用 [cosmic-ray](https://github.com/sixty-north/cosmic-ray) 對 `app.py`、`dbModel.py` 做變異測試(mutmut 3 會跳過有 decorator 的函式,而本專案的路由全都有 decorator,所以不適用)。

```cmd
cosmic-ray init cosmic-ray.toml session.sqlite
cosmic-ray baseline cosmic-ray.toml
cosmic-ray exec cosmic-ray.toml session.sqlite
cr-report session.sqlite --surviving-only
```

注意 cosmic-ray 執行時會直接改寫原始碼檔案、跑完再還原,執行前請先 commit,中途不要強制中斷。

目前結果:119 個 mutants 殺掉 114 個,存活的 5 個都是等價 mutant(改了也不影響行為):

| 位置 | Mutant | 為什麼等價 |
| --- | --- | --- |
| `login()` / `register()` | `request.method != 'POST'` → `<` | 會進到 view 的只有 GET、HEAD、POST,三者 `< 'POST'` 的結果與 `!=` 相同 |
| `app.secret_key` | `secrets.token_hex(32)` → `33` | 只是多 1 byte 亂數,一樣安全 |
| `if __name__ == '__main__'` | `==` → `is` / `<=` | `'__main__'` 是 interned 字串;`'app' <= '__main__'` 為 False |

cosmic-ray 只能變異 Python,所以前端 JS 是手動做變異(例如拿掉 CSRF header、拿掉 `escapeHTML`、Shift+Enter 也送出、不等帳號檢查就送出)再跑 `tests/e2e`:18 個殺掉 17 個,存活的是 `register.js` 裡「檢查快取要比對名稱」的條件,因為名稱一改就會觸發 `input` 事件清掉快取,這個條件只是防禦性寫法。

## 執行畫面

簡單的登入、註冊
![alt tag](http://i.imgur.com/XiNxpEQ.jpg)
![alt tag](http://i.imgur.com/4FoQskT.jpg)

聊天室

![alt tag](http://i.imgur.com/ghdeqF7.jpg)

點選照片下方的齒輪，可以上傳自己的照片
![alt tag](http://i.imgur.com/316KdGN.jpg)

## db - SQLite

![alt tag](http://i.imgur.com/LEuKo7o.jpg)
![alt tag](http://i.imgur.com/isOb07Z.jpg)
![alt tag](http://i.imgur.com/fQyhQpn.jpg)

## Deploy

請參考 [flask-socketio gunicorn-web-server](https://flask-socketio.readthedocs.io/en/latest/deployment.html)

專案內附 **Procfile** 範例:

```cmd
web: gunicorn --threads 8 -w 1 app:app
```

`-w 1` 是 Flask-SocketIO 的硬性要求;若需要多 worker 必須搭配 Redis 訊息隊列。

正式環境請設定 `SECRET_KEY` 環境變數;沒設定時每次啟動都會隨機產生,重啟後所有人都需要重新登入。

從舊版升級時請先執行 `flask db upgrade`(放寬 `Password` 欄位長度)。舊版用 MD5 存的密碼仍可登入,登入成功時會自動換成加鹽的 hash。

## 執行環境

* Python 3.13.13
* Flask 3.1 / Flask-SocketIO 5.6 / SQLAlchemy 2.0 / Pillow 12

## Reference

* [Flask-SocketIO](https://flask-socketio.readthedocs.io/)
* [python-socketio](https://github.com/miguelgrinberg/python-socketio)
* [Flask-Login](https://flask-login.readthedocs.io/)
* [Pillow](https://pillow.readthedocs.io/)
* [Bootstrap 5](https://getbootstrap.com/)
* [聊天室版型](http://www.bypeople.com/minimal-css-chat-ui/)

## License

MIT license
