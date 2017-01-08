from flask import *
from flask_socketio import SocketIO, emit, join_room
from flask_login import UserMixin, LoginManager, login_required, current_user, login_user, logout_user
from dModel import *
from functools import wraps
from PIL import Image
import base64, io, os, uuid

MugShot_PATH = 'static/mugshot'
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
MugShot_FOLDER = os.path.join(APP_ROOT, MugShot_PATH)

app = Flask(__name__)
app.secret_key = 'super secret string'  # Change this!
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.session_protection = "strong"
login_manager.login_view = "login"
login_manager.login_message = "Please LOG IN"
login_manager.login_message_category = "info"

socketio = SocketIO(app)
async_mode = "eventlet"


class User(UserMixin):
    pass


def to_json(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        get_fun = func(*args, **kwargs)
        return json.dumps(get_fun)

    return wrapper


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
    user_id = session.get('user_id')

    Messages_data = db.session.query(
        Message,
        UserAccounts.MugShot
    ).join(
        UserAccounts,
        UserAccounts.UserName == Message.UserName
    ).all()

    MugShot_title = UserAccounts.query.filter_by(UserName=user_id).first().MugShot
    messages_dic = {}
    messages_list = []
    for messages_data in Messages_data:
        messages_dic['data'] = []
        messages_dic['UserName'] = messages_data.Message.UserName
        messages_dic['Messages'] = messages_data.Message.Messages
        messages_dic['MugShot'] = messages_data.MugShot
        messages_dic['CreateDate'] = messages_data.Message.CreateDate.strftime('%H:%M')
        messages_list.append(messages_dic)
        messages_dic = {}
    return render_template("index.html", **locals())


@app.route('/login', methods=['GET', 'POST'])
def login():
    user_id = session.get('user_id')

    if request.method == 'GET':
        return render_template("login.html")

    if current_user.is_authenticated and query_user(user_id):
        return redirect(url_for('index'))

    username = request.form['username']
    user = UserAccounts.query.filter_by(UserName=username).first()
    if user == None:
        return render_template("login.html", error="username or password error")
    pw_form = UserAccounts.psw_to_md5(request.form['password'])
    pw_db = user.Password
    if pw_form == pw_db:
        user = User()
        user.id = username
        login_user(user, remember=True)
        flash('Logged in successfully')
        return redirect(url_for('index'))
    return render_template("login.html", error="username or password error")


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template("register.html")
    username = request.form['username']
    password = request.form['password']
    newAccount = UserAccounts(UserName=username, Password=password, MugShot="default.jpg")
    db.session.add(newAccount)
    db.session.commit()
    return redirect(url_for("index"))


@app.route('/API_check_UserNameExist', methods=['POST'])
@to_json
def API_check_UserNameExist():
    username = request.json['username']
    user = UserAccounts.query.filter_by(UserName=username).first()
    if user == None:
        return "44"
    return "11"


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
def sendInquiry(msg):
    user_id = session.get('user_id')
    CreateDate = datetime.now()

    data_Message = Message(
        UserName=user_id,
        Messages=msg['msg'],
        CreateDate=CreateDate
    )
    db.session.add(data_Message)
    db.session.commit()
    MugShot = UserAccounts.query.filter_by(UserName=user_id).first().MugShot
    data = {
        'time': CreateDate.strftime('%H:%M'),
        'Name': user_id,
        'PictureUrl': MugShot,
        'msg': msg['msg'],
    }
    emit('getInquiry', data, room=msg['room'])


@app.route('/croppic', methods=['GET', 'POST'])
def croppic():
    user_id = session.get('user_id')
    try:
        # imgUrl 		// your image path (the one we recieved after successfull upload)
        imgUrl = request.form['imgUrl']
        # imgInitW  	// your image original width (the one we recieved after upload)
        imgInitW = request.form['imgInitW']
        # imgInitH 	    // your image original height (the one we recieved after upload)
        imgInitH = request.form['imgInitH']
        # imgW 		    // your new scaled image width
        imgW = request.form['imgW']
        # imgH 		    // your new scaled image height
        imgH = request.form['imgH']
        # imgX1 		// top left corner of the cropped image in relation to scaled image
        imgX1 = request.form['imgX1']
        # imgY1 		// top left corner of the cropped image in relation to scaled image
        imgY1 = request.form['imgY1']
        # cropW 		// cropped image width
        cropW = request.form['cropW']
        # cropH 		// cropped image height
        cropH = request.form['cropH']
        angle = request.form['rotation']

        # original size
        imgInitW, imgInitH = int(imgInitW), int(imgInitH)

        # Adjusted size
        imgW, imgH = int(float(imgW)), int(float(imgH))
        imgY1, imgX1 = int(float(imgY1)), int(float(imgX1))
        cropW, cropH = int(float(cropW)), int(float(cropH))
        angle = int(angle)

        # image_format = imgUrl.split(';base64,')[0].split('/')[1]
        title_head = imgUrl.split(',')[0]
        img_data = imgUrl.split('base64,')[1]
        imgData = base64.b64decode(img_data)

        source_image = Image.open(io.BytesIO(imgData))
        image_format = source_image.format.lower()
        # create new crop image
        source_image = source_image.resize((imgW, imgH), Image.ANTIALIAS)

        rotated_image = source_image.rotate(-float(angle), Image.BICUBIC)
        rotated_width, rotated_height = rotated_image.size
        dx = rotated_width - imgW
        dy = rotated_height - imgH
        cropped_rotated_image = Image.new('RGBA', (imgW, imgH))
        cropped_rotated_image.paste(rotated_image.crop((dx / 2, dy / 2, dx / 2 + imgW, dy / 2 + imgH)),
                                    (0, 0, imgW, imgH))

        final_image = Image.new('RGBA', (cropW, cropH), 0)
        final_image.paste(cropped_rotated_image.crop((imgX1, imgY1, imgX1 + cropW, imgY1 + cropH)),
                          (0, 0, cropW, cropH))

        uuid_name = str(uuid.uuid1())
        mugshot = '{}.{}'.format(uuid_name, image_format)
        user_mugshot = UserAccounts.query.filter_by(UserName=user_id).first()
        if user_mugshot.MugShot != "default.jpg":
            delete_filename = '{}/{}'.format(MugShot_FOLDER, user_mugshot.MugShot)
            os.remove(delete_filename)

        user_mugshot.MugShot = mugshot
        db.session.add(user_mugshot)
        db.session.commit()
        savePath = '{}/{}'.format(MugShot_FOLDER, mugshot)
        final_image.save(savePath)

        #  The crop rectangle, as a (left, upper, right, lower)-tuple.
        # box = (imgX1, imgY1, imgX1 + cropW, imgY1 + cropH)
        # newImg = source_image.crop(box)
        # imgByteArr = io.BytesIO()
        # newImg.save(imgByteArr, format=image_format)
        # imgByteArr = imgByteArr.getvalue()
        # imgbase = base64.b64encode(imgByteArr).decode('utf-8')
        # img_base64 = '{},{}'.format(title_head, imgbase)

        data = {
            'status': 'success',
            'url': '/{}/{}'.format(MugShot_PATH, mugshot),
            'filename': mugshot
        }
        return json.dumps(data)
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e),
        }


if __name__ == '__main__':
    socketio.run(app)
