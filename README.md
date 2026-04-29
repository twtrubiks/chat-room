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

## 啟動

```cmd
python app.py
```

預設會在 `http://localhost:5000` 啟動，使用 Flask-SocketIO 內建的開發伺服器。

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
