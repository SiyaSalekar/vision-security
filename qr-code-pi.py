import cv2
from flask import Flask, render_template, request, redirect
import os
import mysql.connector
import bcrypt
import qrcode
import RPi.GPIO as GPIO
import time

# pubnub imports
from pubnub.callbacks import SubscribeCallback
from pubnub.enums import PNStatusCategory, PNOperationType
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub

myChannel = 'siyas-channel'
sensorsList = ["cam"]
dataD = {}

pnconfig = PNConfiguration()

pnconfig.subscribe_key = ''
pnconfig.publish_key = ''
pnconfig.user_id = "siyas-machine"
pubnub = PubNub(pnconfig)

app = Flask(__name__)

# # database connect
mydb = mysql.connector.connect(
    host='localhost',
    user='root',
    password='Siya@123',
    database='vision_security'
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
    name = request.form.get("student_name")
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
    img.save(f"templates/images/{name}.png")

    if not student_id:
        return render_template("error.html", message="Invalid ID")
    if not name:
        return render_template("error.html", message="Enter Name")
    mycursor = mydb.cursor()
    mycursor.execute("insert into student(name, student_id, password) values (%s, %s, %s) ",
                     (name, student_id, password_store))
    mydb.commit()
    mycursor.close()
    return redirect("/")


@app.route("/qrgenerate")
def qrscan():
    dataD["alarm"] = False
    trigger = False
    # set up camera object
    cap = cv2.VideoCapture(0)

    # QR code detection object
    detector = cv2.QRCodeDetector()
    while True:
        # get the image
        _, img = cap.read()
        # get bounding box coords and data
        data, bbox, _ = detector.detectAndDecode(img)

        # if there is a bounding box, draw one, along with the data
        if (bbox is not None):

            cv2.putText(img, data, (int(bbox[0][0][0]), int(bbox[0][0][1]) - 10), cv2.FONT_HERSHEY_SIMPLEX,
                        0.5, (0, 255, 0), 2)
            if data:
                mycursor = mydb.cursor()
                mycursor.execute("select password from student where password = %s", [data])
                fetched_data = mycursor.fetchone()

                if fetched_data is None:
                    print("INVALID DATA")
                    publish(myChannel, {"Data": "Invalid"})
                    return render_template("qr-code.html", someVariable="Invalid")
                else:
                    if fetched_data[0] == data:
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
                        publish(myChannel, {"Data": "Valid"})

                        GPIO.cleanup()
                        mycursor.close()
                        return render_template("qr-code.html", someVariable="Valid")

        # display the image preview
        cv2.imshow("code detector", img)
        if (cv2.waitKey(1) == ord("q")):
            break

    # free camera object and exit
    cap.release()
    cv2.destroyAllWindows()


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
            if key[0] == "event":  # {"event":{"sensor_name":True}}
                self.handleEvent(msg)
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


pubnub.add_listener(MySubscribeCallback())
pubnub.subscribe().channels(myChannel).execute()


if __name__ == '__main__':
    app.run(host='192.168.43.136', port=9000)
    pubnub.add_listener(MySubscribeCallback())
    pubnub.subscribe().channels(myChannel).execute()

    # server = Server(app.wsgi_app)
    # server.serve()



