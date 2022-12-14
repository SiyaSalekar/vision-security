import cv2
from flask import Flask, render_template, request, redirect, json
import os
import mysql.connector
import bcrypt
import qrcode
import RPi.GPIO as GPIO
import time
from flask_sqlalchemy import SQLAlchemy

# pubnub imports
from pubnub.callbacks import SubscribeCallback
from pubnub.enums import PNStatusCategory, PNOperationType
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub

myChannel = 'siyas-channel'
sensorsList = ["led"]
dataD = {}
data = {}

pnconfig = PNConfiguration()
pnconfig.subscribe_key = "sub-c-babca055-8ae8-4cbb-87e3-d1927bc7826a"
pnconfig.publish_key = "pub-c-7b7bf3ef-a5df-4ec8-9bb2-f70cc90f6c86"
pnconfig.user_id = "Jack-device"
pubnub = PubNub(pnconfig)

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://siyas:Qwerty1234567!@54.211.151.170/vision_sec'
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class DetailTable(db.Model):
    __tablename__ = "student_register"
    s_id = db.Column(db.Integer, primary_key=True)
    student_number = db.Column(db.String(30))
    student_password = db.Column(db.String(30))

    # constructor
    def __init__(self, student_number, student_password):
        self.student_number = student_number
        self.student_password = student_password


# database connect
mydb = mysql.connector.connect(
    host='54.211.151.170',
    user='siyas',
    password='Qwerty1234567!',
    database='vision_sec'
)


# database connect endRegion


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("index.html")
    elif request.method == "POST":
        return render_template("greet.html", name=request.form.get("name", "World"))


@app.route("/register", methods=["POST"])
def register():
    student_id = request.form.get("student_id")
    email = request.form.get("student_email")
    end_date = request.form.get("end_date")
    if not student_id:
        return render_template("error.html", message="Invalid ID")
    if not email:
        return render_template("error.html", message="Invalid Email")
    if not end_date:
        return render_template("error.html", message="Invalid End Date")

    # convert passwd to bytes
    passwd = request.form.get("password").encode()

    # hashing password
    password = bcrypt.hashpw(passwd, bcrypt.gensalt())
    password_store = str(password)

    qr = qrcode.QRCode(version=1,
                       error_correction=qrcode.constants.ERROR_CORRECT_M,
                       box_size=10, border=4)
    qr.add_data(password_store)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    img.save(f"static/images/{student_id}.png")
    mycursor = mydb.cursor()
    mycursor.execute(
        "insert into student(student_number, student_email, student_password, course_end_date) values (%s, %s, %s, %s) ",
        (student_id, email, password_store, end_date))
    mydb.commit()
    mycursor.close()
    return redirect("/")


def get_student(student_password):
    get_user_row = DetailTable.query.filter_by(student_password=student_password).first()
    if get_user_row is not None:
        return get_user_row
    else:
        print("Student doesnt exist")
        return False


# pubnub code

def publish(custom_channel, msg):
    pubnub.publish().channel(custom_channel).message(msg).pn_async(my_publish_callback)


def my_publish_callback(envelope, status):
    # Check whether request successfully completed or not
    if not status.is_error():
        pass  # Message successfully published to specified channel.
    else:
        pass  # Handle message publish error. Check 'category' property to find out possible issue
        # because of which request did fail.
        # Request can be resent using: [status retry];


class MySubscribeCallback(SubscribeCallback):

    def presence(self, pubnub, presence):
        pass  # handle incoming presence data

    def status(self, pubnub, status):
        if status.category == PNStatusCategory.PNUnexpectedDisconnectCategory:
            pass  # This event happens when radio / connectivity is lost

        elif status.category == PNStatusCategory.PNConnectedCategory:
            # Connect event. You can do stuff like publish, and know you'll get it.
            # Or just use the connected event to confirm you are subscribed for
            # UI / internal notifications, etc
            pubnub.publish().channel(myChannel).message('Connected to PubNub').pn_async(my_publish_callback)
        elif status.category == PNStatusCategory.PNReconnectedCategory:
            pass
            # Happens as part of our regular operation. This event happens when
            # radio / connectivity is lost, then regained.
        elif status.category == PNStatusCategory.PNDecryptionErrorCategory:
            pass
            # Handle message decryption error. Probably client configured to
            # encrypt messages and on live data feed it received plain text.

    def message(self, pubnub, message):
        # Handle new message stored in message.message
        try:
            print(message.message)
            msg = message.message
            key = list(msg.keys())
            print(key)
            if key[0] == "event":  # {"event":{"sensor_name":True}}
                self.handleEvent(msg)
            if key[0] == "scan":
                self.qrgenerate()
        except Exception as e:
            print("Received: ", message.message)
            print(e)
            pass

    def handleEvent(self, msg):
        global dataD
        eventData = msg["event"]
        key = list(eventData.keys())
        if key[0] in sensorsList:
            if eventData[key[0]] is True:
                dataD["alarm"] = True
            if eventData[key[0]] is False:
                dataD["alarm"] = False

    def qrgenerate(self):
        dataD["alarm"] = False
        trigger = False
        # set up camera object
        cap = cv2.VideoCapture(-1)

        # QR code detection object
        detector = cv2.QRCodeDetector()
        while True:
            # get the image
            _, img = cap.read()
            # get bounding box coords and data
            data['content'], bbox, _ = detector.detectAndDecode(img)

            # if there is a bounding box, draw one, along with the data
            if (bbox is not None):

                cv2.putText(img, data['content'], (int(bbox[0][0][0]), int(bbox[0][0][1]) - 10),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5, (0, 255, 0), 2)
                cv2.imshow("code detector", img)
                if data['content']:
                    mycursor = mydb.cursor()
                    mycursor.execute("select student_password from student_register where student_password = %s",
                                     [data['content']])
                    fetched_data = mycursor.fetchone()
                    # fetched_data = get_student(data['content'])

                    if fetched_data is None:
                        # Buzzer setup
                        GPIO.setwarnings(False)
                        GPIO.setmode(GPIO.BOARD)
                        GPIO.setup(10, GPIO.OUT)
                        # control Buzzer when data received invalid- set output to HIGH
                        for i in range(0, 6):
                            for pulse in range(60):
                                GPIO.output(10, True)
                                time.sleep(0.001)
                                GPIO.output(10, False)
                                time.sleep(0.001)
                            time.sleep(0.02)
                        publish(myChannel, {"data": "invalid"})
                        data['Found'] = "false"
                        parsed_json = json.dumps(data)
                        cap.release()
                        cv2.destroyAllWindows()
                        return
                    else:
                        if fetched_data[0] == data['content']:
                            print("data Valid")
                            # LED setup
                            GPIO.setmode(GPIO.BOARD)
                            GPIO.setup(8, GPIO.OUT)

                            # control LED when data received - set output to HIGH
                            for i in range(0, 1):
                                GPIO.output(8, True)
                                time.sleep(0.5)
                                GPIO.output(8, False)
                                time.sleep(0.5)
                            trigger = True
                            publish(myChannel, {"data": "valid"})
                            GPIO.cleanup()
                            mycursor.close()
                            data['Found'] = "true"
                            parsed_json = json.dumps(data)
                            cap.release()
                            cv2.destroyAllWindows()
                            return str(parsed_json)

            # display the image preview
            cv2.imshow("code detector", img)
            if (cv2.waitKey(1) == ord("q")):
                break

        # free camera object and exit
        cap.release()
        cv2.destroyAllWindows()


pubnub.add_listener(MySubscribeCallback())
pubnub.subscribe().channels(myChannel).execute()

if __name__ == '__main__':
    app.run(host='192.168.43.136', port=9000)
    pubnub.add_listener(MySubscribeCallback())
    pubnub.subscribe().channels(myChannel).execute()

    # server = Server(app.wsgi_app)
    # server.serve()

