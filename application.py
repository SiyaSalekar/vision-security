import cv2
from flask import Flask, render_template, request, redirect, json
import os
from flask_mysqldb import MySQL
import bcrypt
import qrcode

app = Flask(__name__)

data = {}

# ----Begin Ovidiu's Code
#this is path to images to  be used with flask and HTML.

IMAGES=os.path.join('static', 'images')

app.config['UPLOAD_FOLDER'] = IMAGES

placeholder_image=os.path.join(app.config['UPLOAD_FOLDER'], 'placeholder_image.jpg')
# ----End Ovidiu's Code

# --------Begin Siya's Code
# database connect
app.config['MYSQL'] = 'localhost'
app.config["MYSQL_USER"] = os.getenv("MYSQL_USER")
app.config["MYSQL_PASSWORD"] = os.getenv("MYSQL_PASSWORD")
app.config["MYSQL_DB"] = 'vision_security'

mysql = MySQL(app)

# database connect endRegion

@app.route("/", methods = ["GET","POST"])
def index():
    if request.method == "GET":
        return render_template("index.html")
    elif request.method == "POST":
        return render_template("greet.html", name=request.form.get("name", "World"))


@app.route("/register",methods=["POST"])
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

    cursor = mysql.connection.cursor()
    cursor.execute("insert into student(student_number, student_email, student_password, course_end_date) values (%s, %s, %s, %s) ", (student_id, email, password_store, end_date))
    mysql.connection.commit()
    cursor.close()
    return redirect("/")


@app.route("/qrgenerate")
def qrgenerate():
    # set up camera object
    cap = cv2.VideoCapture(0)

    # QR code detection object
    detector = cv2.QRCodeDetector()
    while True:
        # get the image
        _, img = cap.read()
        # get bounding box co-ords and data

        data['content'], bbox, _ = detector.detectAndDecode(img)

        # if there is a bounding box, draw one, along with the data
        if (bbox is not None):

            cv2.putText(img, data['content'], (int(bbox[0][0][0]), int(bbox[0][0][1]) - 10), cv2.FONT_HERSHEY_SIMPLEX,
                        0.5, (0, 255, 0), 2)
            if data['content']:

                cursor = mysql.connection.cursor()
                cursor.execute("select student_password from student where student_password = %s", [data['content']])
                fetched_data = cursor.fetchone()

                if fetched_data is None:
                    data['Found'] = "false"
                    parsed_json = json.dumps(data)
                    return str(parsed_json)
                    #return "Invalid"
                    #return render_template("qr-code.html", someVariable="Invalid")
                else:
                    if fetched_data[0] == data['content']:
                        cursor.close()
                        data['Found'] = "true"
                        parsed_json = json.dumps(data)
                        return str(parsed_json)
                        #return render_template("qr-code.html", someVariable="Valid")


        # display the image preview
        cv2.imshow("code detector", img)
        if (cv2.waitKey(1) == ord("q")):
            break

    # free camera object and exit
    cap.release()
    cv2.destroyAllWindows()


# -------End Siya's Code

if __name__ == '__main__':
    app.run()