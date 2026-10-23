from flask import Flask, redirect, render_template, request, flash, url_for, jsonify
from flask_socketio import SocketIO, emit, join_room
from flask_login import UserMixin, LoginManager, login_required, current_user, login_user, logout_user
from flask_migrate import Migrate
from sqlalchemy.exc import IntegrityError
from dbModel import UserAccounts, Message, db
from PIL import Image
from datetime import datetime
import os
import secrets
import uuid

MugShot_PATH = 'static/mugshot'
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
MugShot_FOLDER = os.path.join(APP_ROOT, MugShot_PATH)

app = Flask(__name__)
# 正式環境請設定 SECRET_KEY；沒設的話每次啟動隨機產生，重啟後所有人都要重新登入
app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:xxxxx@localhost/db'
db.init_app(app)
migrate = Migrate(app, db, render_as_batch=True)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.session_protection = "strong"
login_manager.login_view = "login"
login_manager.login_message = "Please LOG IN"
login_manager.login_message_category = "info"

socketio = SocketIO(app, async_mode='threading')


class User(UserMixin):
    pass


def query_user(username):
    user = UserAccounts.query.filter_by(UserName=username).first()
    if user:
        return True
    return False


@login_manager.user_loader
def user_loader(username):
    if query_user(username):
        user = User()
        user.id = username
        return user
    return None


@app.route('/')
@app.route('/index', methods=['GET'])
@login_required
def index():
    user_id = current_user.id

    message_data = db.session.query(
        Message,
        UserAccounts.MugShot
    ).join(
        UserAccounts,
        UserAccounts.UserName == Message.UserName
    ).order_by(
        Message.CreateDate,
        Message.Id
    ).all()

    mug_shot_title = UserAccounts.query.filter_by(UserName=user_id).first().MugShot
    messages_dic = {}
    messages_list = []
    for message in message_data:
        messages_dic['data'] = []
        messages_dic['UserName'] = message.Message.UserName
        messages_dic['Messages'] = message.Message.Messages
        messages_dic['MugShot'] = message.MugShot
        messages_dic['CreateDate'] = message.Message.CreateDate.strftime('%H:%M')
        messages_list.append(messages_dic)
        messages_dic = {}
    return render_template("index.html", **locals())


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method != 'POST':
        return render_template("login.html")

    username = request.form['username']
    password = request.form['password']
    account = UserAccounts.query.filter_by(UserName=username).first()
    if not account or not account.check_password(password):
        return render_template("login.html", error="username or password error")
    if account.is_legacy_hash():
        # 舊帳號的密碼是 MD5，登入成功時順便換成加鹽的 hash
        account.set_password(password)
        db.session.commit()
    user = User()
    user.id = username
    login_user(user, remember=True)
    flash('Logged in successfully')
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method != 'POST':
        return render_template("register.html")
    username = request.form.get('username', '')
    password = request.form.get('password', '')
    if not username or not password:
        return render_template("register.html", error="username and password are required")
    new_account = UserAccounts(user_name=username, password=password, mugshot="default.jpg")
    db.session.add(new_account)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return render_template("register.html", error="UserName already exists.")
    return redirect(url_for("index"))


@app.route('/API_check_UserNameExist', methods=['POST'])
def api_check_user_name_exist():
    username = (request.form.get('username')
                or (request.get_json(silent=True) or {}).get('username'))
    if not username:
        return jsonify(False)
    user = UserAccounts.query.filter_by(UserName=username).first()
    return jsonify(user is None)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@socketio.on('join')
def join(message):
    join_room(message['room'])
    print('join')


@socketio.on('connect')
def test_connect():
    # Userid = session.get('UserId')
    # print(Userid, 'connectd')
    print('connect')


@socketio.on('sendInquiry')
def send_inquiry(msg):
    if not current_user.is_authenticated:
        return
    user_id = current_user.id
    create_date = datetime.now()

    data_message = Message(
        user_name=user_id,
        messages=msg['msg'],
        create_date=create_date
    )
    db.session.add(data_message)
    db.session.commit()
    mug_shot = UserAccounts.query.filter_by(UserName=user_id).first().MugShot
    data = {
        'time': create_date.strftime('%H:%M'),
        'Name': user_id,
        'PictureUrl': mug_shot,
        'msg': msg['msg'],
    }
    emit('getInquiry', data, room=msg['room'])


@app.route('/croppic', methods=['POST'])
@login_required
def croppic():
    user_id = current_user.id
    file = request.files.get('image')
    if not file:
        return jsonify(status='error', message='no image'), 400
    try:
        img = Image.open(file.stream)
        img.verify()
        file.stream.seek(0)
        img = Image.open(file.stream)
        fmt = (img.format or 'PNG').lower()

        mugshot = '{}.{}'.format(uuid.uuid1(), fmt)
        save_path = os.path.join(MugShot_FOLDER, mugshot)
        img.save(save_path)

        user = UserAccounts.query.filter_by(UserName=user_id).first()
        if user.MugShot != "default.jpg":
            old = os.path.join(MugShot_FOLDER, user.MugShot)
            if os.path.exists(old):
                os.remove(old)
        user.MugShot = mugshot
        db.session.commit()

        return jsonify(
            status='success',
            url='/{}/{}'.format(MugShot_PATH, mugshot),
            filename=mugshot,
        )
    except Exception as e:
        return jsonify(status='error', message=str(e)), 500


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
