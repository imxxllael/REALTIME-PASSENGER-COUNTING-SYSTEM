from flask import Flask, session, render_template, request, redirect, url_for
import pymysql.cursors
from werkzeug.security import generate_password_hash, check_password_hash
import urllib.request
import time
import numpy as np
import cv2 as cv
import Person
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from flask import Flask, render_template, Response
from ultralytics import YOLO
import logging

app = Flask(__name__)
logger = logging.getLogger(__name__)

# configure the database
connection = pymysql.connect(
    host='localhost',
    user='username',
    password='pass',
    db='databasename',
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)

# function to check if user is logged in
app.secret_key = ''

def is_logged_in():
    return 'username' in session

@app.route('/')
def index():
    return render_template('index.html', css_file=url_for('static', filename='css/index.css'))

@app.route('/log')
def get_log():
    with open('log.txt', 'r') as log_file:
        log_data = log_file.read()
    return log_data

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # get the input values
        username = request.form['username']
        password = request.form['password']

        try:
            # validate user input
            with connection.cursor() as cursor:
                sql = "SELECT * FROM users WHERE username = %s"
                cursor.execute(sql, (username,))
                result = cursor.fetchone()

                if not result:
                    error = "Invalid username or password"
                    return render_template('login.html', css_file=url_for('static', filename='css/login.css'), error=error)

                # compare the password hash to the stored hash
                hashed_password = result['password']

                if check_password_hash(hashed_password, password):
                    # create a session for the user
                    session['username'] = username

                    # redirect to the dashboard page
                    return redirect('/dashboard')

                else:
                    error = "Invalid username or password"
                    return render_template('login.html', css_file=url_for('static', filename='css/login.css'), error=error)

        except Exception as e:
            print(f"Error: {e}")
            connection.rollback()

        finally:
            connection.close()

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # get the input values
        name = request.form['name']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # validate user input
        with connection.cursor() as cursor:
            sql = "SELECT * FROM users WHERE username = %s"
            cursor.execute(sql, (username,))
            result = cursor.fetchone()

            if result:
                error = "Username already exists"
                return render_template('register.html', css_file=url_for('static', filename='css/register.css'), error=error)

            # hash password
            hashed_password = generate_password_hash(password)

            # insert user into database
            sql = "INSERT INTO users (name, username, email, password) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (name, username, email, hashed_password))
            connection.commit()

            # create session for user
            session['username'] = username

            # redirect to login page
            return redirect(url_for('login'))

    return render_template('register.html', css_file=url_for('static', filename='css/register.css'))

# check if user is logged in
@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']
    return render_template('dashboard33.html', username=username)

@app.route('/location')
def location():
    
    return render_template('newlocation.html')


@app.route('/logs', methods=['GET', 'POST'])
def logs():
    try:
        with connection.cursor() as cursor:
            # Fetch bus data from the database
            sql = "SELECT bus_number FROM buses"
            cursor.execute(sql)
            result = cursor.fetchall()

            options = ""
            if result:
                for row in result:
                    busNumber = row['bus_number']
                    options += f"<option value='{busNumber}'>{busNumber}</option>"

        if request.method == 'POST':
            search_value = request.form['search']

            try:
                with connection.cursor() as cursor:
                    sql = "SELECT * FROM buses WHERE bus_number=%s"
                    cursor.execute(sql, (search_value,))
                    result = cursor.fetchall()

                    if result:
                        output = "<div id='header'>Real-time Bus Inspector</div>"
                        output += "<div id='content'>"
                        for row in result:
                            output += f"<p>Bus Number: {row['bus_number']}</p>"
                            output += f"<p>Capacity: {row['capacity']}</p>"
                            output += f"<p>Route: {row['route']}</p>"
                            output += f"<p>Driver Name: {row['driver_name']}</p>"
                            output += f"<p>Driver Contact: {row['driver_contact']}</p>"
                            output += f"<p>Driver License: {row['driver_license']}</p>"
                        output += "</div>"
                        return output
                    else:
                        return "<div id='header'>Real-time Bus Inspector</div><div id='content'><p>No results found.</p></div>"
            except Exception as e:
                return f"Error: {str(e)}"

        with open('log.txt', 'r') as file:
            log_content = file.read()

        return render_template('travellogs.html', options=options, log_content=log_content)

    except Exception as e:
        return f"Error: {str(e)}"


@app.route('/bus', methods=['GET', 'POST'])
def bus():
    if request.method == 'POST':
        bus_number = request.form['bus_number']
        capacity = request.form['capacity']
        route = request.form['route']
        driver_name = request.form['driver_name']
        driver_contact = request.form['driver_contact']

        if bus_number and capacity and route and driver_name and driver_contact:
            with connection.cursor() as cursor:
                # Check if the record already exists
                sql = "SELECT * FROM buses WHERE bus_number = %s"
                cursor.execute(sql, (bus_number,))
                result = cursor.fetchone()

                if result:
                    # Record already exists, handle accordingly (e.g., show an error message)
                    return "Bus record already exists"

                else:
                    # Insert the new record
                    sql = "INSERT INTO buses (bus_number, capacity, route, driver_name, driver_contact) VALUES (%s, %s, %s, %s, %s)"
                    cursor.execute(sql, (bus_number, capacity, route, driver_name, driver_contact))
                    connection.commit()
                    session['submitted'] = True
                    return redirect(url_for('bus'))

    elif request.method == 'POST' and 'update_id' in request.form:
        update_id = request.form['update_id']
        bus_number = request.form['bus_number']
        capacity = request.form['capacity']
        route = request.form['route']
        driver_name = request.form['driver_name']
        driver_contact = request.form['driver_contact']

        with connection.cursor() as cursor:
            # Update the bus record
            sql = "UPDATE buses SET bus_number=%s, capacity=%s, route=%s, driver_name=%s, driver_contact=%s WHERE id=%s"
            cursor.execute(sql, (bus_number, capacity, route, driver_name, driver_contact, update_id))
            connection.commit()

        return redirect(url_for('index') + '#buses-container')

    elif request.method == 'GET' and 'delete_id' in request.args:
        delete_ids = request.args.getlist('delete_id')

        with connection.cursor() as cursor:
            # Delete the records
            sql = "DELETE FROM buses WHERE id = %s"
            for delete_id in delete_ids:
                cursor.execute(sql, (delete_id,))
            connection.commit()

        return redirect(url_for('index') + '#buses-container')

    # Fetch the data from the database
    with connection.cursor() as cursor:
        sql = "SELECT * FROM buses"
        cursor.execute(sql)
        result = cursor.fetchall()

    return render_template('buses.html', buses=result)



logger.setLevel(logging.INFO)

# create a file handler
handler = logging.FileHandler('log.txt')
handler.setLevel(logging.INFO)

# create a logging format
formatter = logging.Formatter()
handler.setFormatter(formatter)

# add the handlers to the logger
logger.addHandler(handler)


cnt_enter  = 0
cnt_exit = 0
cnt_inside = 0
cnt_total=0

# Fetch the service account key JSON file contents
cred = credentials.Certificate('Inspectorfile\esp32tofirebase-a5fda-firebase-adminsdk-zs1e0-af2bd074bb.json')

# Initialize the app with a service account, granting admin privileges
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://esp32tofirebase-a5fda-default-rtdb.asia-southeast1.firebasedatabase.app/'
})

# Get a reference to the database
ref = db.reference('/GPS')

# Get the location data
location_data = ref.get()

# Update the location data
ref.update({
    'f_latitude': location_data['f_latitude'],
    'f_longitude': location_data['f_longitude']
})

# Entry and exit counters
url= 'http://192.168.0.94/cam-hi.jpg'

h = 650
w = 1500
frameArea = h * w
areaTH = frameArea / 250
print('Area Threshold', areaTH)

# Input/output lines
line_up = int(2*(h/5))
line_down   = int(3*(h/5))

up_limit =   int(1*(h/5))
down_limit = int(4*(h/5))

print("Red line y:", str(line_down))
print("Blue line y:", str(line_up))
line_down_color = (255, 0, 0)
line_up_color = (0, 0, 255)
pt1 = [0, line_down]
pt2 = [w, line_down]
pts_L1 = np.array([pt1, pt2], np.int32)
pts_L1 = pts_L1.reshape((-1, 1, 2))
pt3 = [0, line_up]
pt4 = [w, line_up]
pts_L2 = np.array([pt3, pt4], np.int32)
pts_L2 = pts_L2.reshape((-1, 1, 2))

pt5 = [0, up_limit]
pt6 = [w, up_limit]
pts_L3 = np.array([pt5, pt6], np.int32)
pts_L3 = pts_L3.reshape((-1, 1, 2))
pt7 = [0, down_limit]
pt8 = [w, down_limit]
pts_L4 = np.array([pt7, pt8], np.int32)
pts_L4 = pts_L4.reshape((-1, 1, 2))

# Initialize YOLO model
Model = YOLO('yolov8s.pt')

# Variables
font = cv.FONT_HERSHEY_SIMPLEX
persons = []
max_p_age = 4
pid = 1


def gen_frames():
    cnt_enter  = 0
    cnt_exit = 0
    cnt_inside = 0
    cnt_total=0
    persons = []
    max_p_age = 4
    pid = 1

    while True:
        img_resp = urllib.request.urlopen(url)
        img_np = np.array(bytearray(img_resp.read()), dtype=np.uint8)
        frame = cv.imdecode(img_np, -1)
            
        if frame is not None:
            for i in persons:
                i.age_one()  # age every person one frame

            # Detect objects using YOLO
            results = Model(frame, verbose=False)

            for obj in results[0].boxes.data:
                x, y, x2, y2, conf, cls = int(obj[0]), int(obj[1]), int(obj[2]), int(obj[3]), obj[4], int(obj[5])
                if cls == 0 and conf >= 0.7:  # Assuming class 0 represents persons
                    new = True
                    cx = int((x + x2) / 2)
                    cy = int((y + y2) / 2)
                    if cy in range(up_limit, down_limit):
                        person_passed = False  # Flag to track if a person has already been counted
                        for i in persons:
                            if abs(cx - i.getX()) <= (x2 - x) and abs(cy - i.getY()) <= (y2 - y):
                                new = False
                                i.updateCoords(cx, cy)  # updates coordinates on the object and resets age
                                if i.going_UP(line_down, line_up):
                                    if not person_passed:
                                        cnt_enter += 1
                                        person_passed = True
                                    cnt_total += 1
                                    cnt_inside += 1
                                    logger.info("Person Entered on " + time.strftime("%c") + ' in Location: (' + str(
                                        location_data['f_latitude']) + ', ' + str(location_data['f_longitude']) + ')\n')
                                    logger.info("Total Person Entered: " + str(cnt_enter) + "\n")
                                    logger.info("Total Person Remaining Inside: " + str(cnt_inside) + "\n")
                                    logger.info("Total: " + str(cnt_total) + "\n")
                                elif i.going_DOWN(line_down, line_up):
                                    if not person_passed:
                                        cnt_exit += 1
                                        person_passed = True
                                    cnt_inside -= 1
                                    cnt_total += 1
                                    logger.info("Person Exits on " + time.strftime("%c") + ' in Location: (' + str(
                                        location_data['f_latitude']) + ', ' + str(location_data['f_longitude']) + ')\n')
                                    logger.info("Total Person Exits: " + str(cnt_exit) + "\n")
                                    logger.info("Total Person Remaining Inside: " + str(cnt_inside) + "\n")
                                    logger.info("Total: " + str(cnt_total) + "\n")
                            if i.getState() == '1':
                                if i.getDir() == 'down' and i.getY() > down_limit:
                                    i.setDone()
                                    if not person_passed:
                                        cnt_exit += 1
                                        person_passed = True
                                    cnt_inside -= 1
                                    cnt_total += 1
                                elif i.getDir() == 'up' and i.getY() < up_limit:
                                    i.setDone()
                                    if not person_passed:
                                        cnt_enter += 1
                                        person_passed = True
                                    cnt_total += 1
                                    cnt_inside += 1
                            if i.timedOut():
                                index = persons.index(i)
                                persons.pop(index)
                                del i  # release the memory of i

                        if new == True:
                            p = Person.MyPerson(pid, cx, cy, max_p_age)
                            persons.append(p)
                            pid += 1


                    cv.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
                    img = cv.rectangle(frame, (x, y), (x2, y2), (0, 255, 0), 2)

        ref = db.reference('Passenger')
        ref.update({
            'enter': cnt_enter,
            'exit': cnt_exit,
            'inside': cnt_inside,
            'total': cnt_total
        })

        str_up = 'ENTER: ' + str(cnt_enter)
        str_down = 'EXIT: ' + str(cnt_exit)
        str_remaining = 'REMAINING: ' + str(cnt_enter - cnt_exit)
        str_total = 'TOTAL: ' + str(cnt_enter + cnt_exit)
        frame = cv.polylines(frame, [pts_L1], False, line_down_color, thickness=2)  # blueline
        frame = cv.polylines(frame, [pts_L2], False, line_up_color, thickness=2)  # Redline
        frame = cv.polylines(frame, [pts_L3], False, (255, 255, 255), thickness=1)  # Upline_limit
        frame = cv.polylines(frame, [pts_L4], False, (255, 255, 255), thickness=1)  # Downline_limit
        cv.putText(frame, str_up, (10, 40), font, 0.5, (255, 255, 255), 2, cv.LINE_AA)
        cv.putText(frame, str_up, (10, 40), font, 0.5, (0, 0, 255), 1, cv.LINE_AA)
        cv.putText(frame, str_down, (10, 90), font, 0.5, (255, 255, 255), 2, cv.LINE_AA)
        cv.putText(frame, str_down, (10, 90), font, 0.5, (255, 0, 0), 1, cv.LINE_AA)
        cv.putText(frame, str_remaining, (10, 140), font, 0.5, (255, 255, 255), 2, cv.LINE_AA)
        cv.putText(frame, str_remaining, (10, 140), font, 0.5, (0, 255, 0), 1, cv.LINE_AA)
        cv.putText(frame, str_total, (10, 190), font, 0.5, (255, 255, 255), 2, cv.LINE_AA)
        cv.putText(frame, str_total, (10, 190), font, 0.5, (255, 255, 0), 1, cv.LINE_AA)
        
        ret, buffer = cv.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')     


@app.route('/passenger')
def passenger():
    return render_template('passenger.html')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(debug=True)

