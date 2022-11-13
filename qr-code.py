import cv2
from flask import Flask, render_template
import threading
import os
from flask_mysqldb import MySQL


app = Flask(__name__)

# # database code
# app.config['MYSQL'] = 'localhost'
# app.config["MYSQL_USER"] = os.getenv("MYSQL_USER")
# app.config["MYSQL_PASSWORD"] = os.getenv("MYSQL_PASSWORD")
# app.config["MYSQL_DB"] = 'sd3a_registrants_23'
#
# mysql = MySQL(app)

# database code endRegion

# # pubnub
# from pubnub.callbacks import SubscribeCallback
# from pubnub.enums import PNStatusCategory, PNOperationType
# from pubnub.pnconfiguration import PNConfiguration
# from pubnub.pubnub import PubNub
#
# pnconfig = PNConfiguration()
#
# pnconfig.subscribe_key = 'mySubscribeKey'
# pnconfig.publish_key = 'myPublishKey'
# pnconfig.user_id = "my_custom_user_id"
# pubnub = PubNub(pnconfig)
#
# def my_publish_callback(envelope, status):
#     # Check whether request successfully completed or not
#     if not status.is_error():
#         pass  # Message successfully published to specified channel.
#     else:
#         pass  # Handle message publish error. Check 'category' property to find out possible issue
#         # because of which request did fail.
#         # Request can be resent using: [status retry];
#
# class MySubscribeCallback(SubscribeCallback):
#     def presence(self, pubnub, presence):
#         pass  # handle incoming presence data
#
#     def status(self, pubnub, status):
#         if status.category == PNStatusCategory.PNUnexpectedDisconnectCategory:
#             pass  # This event happens when radio / connectivity is lost
#
#         elif status.category == PNStatusCategory.PNConnectedCategory:
#             # Connect event. You can do stuff like publish, and know you'll get it.
#             # Or just use the connected event to confirm you are subscribed for
#             # UI / internal notifications, etc
#             pubnub.publish().channel('my_channel').message('Hello world!').pn_async(my_publish_callback)
#         elif status.category == PNStatusCategory.PNReconnectedCategory:
#             pass
#             # Happens as part of our regular operation. This event happens when
#             # radio / connectivity is lost, then regained.
#         elif status.category == PNStatusCategory.PNDecryptionErrorCategory:
#             pass
#             # Handle message decryption error. Probably client configured to
#             # encrypt messages and on live data feed it received plain text.
#
#     def message(self, pubnub, message):
#         # Handle new message stored in message.message
#         print(message.message)
#
# pubnub.add_listener(MySubscribeCallback())
# pubnub.subscribe().channels('my_channel').execute()
#
# # pubnub endRegion

@app.route("/")
def index():
    return render_template("index.html")



@app.route("/qrgenerate")
def qrscan():
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
                print("data found: ", data)
                return render_template("qr-code.html", someVariable=data)

        # display the image preview
        cv2.imshow("code detector", img)
        if (cv2.waitKey(1) == ord("q")):
            break

        # free camera object and exit
    cap.release()
    cv2.destroyAllWindows()




# generate QR code
# @app.route('/qrgenerate/studentID')
# def generateCode(studentID):
#     qr = qrcode.QRCode(version=1,
#                        error_correction=qrcode.constants.ERROR_CORRECT_M,
#                        box_size=10,border=4)
#     qr.add_data(studentID)
#     qr.make(fit=True)
#     img = qr.make_image(fill_color='green', back_color = 'white')
#     img.save(f"templates/images/{studentID}.png")
#     return render_template("index.html")
# endRegion generate QR code



if __name__ == '__main__':
    #app.run(host='192.168.43.136',port=9000)
    app.run(debug=True)



