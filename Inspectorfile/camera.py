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
cred = credentials.Certificate('esp32tofirebase-a5fda-firebase-adminsdk-zs1e0-af2bd074bb.json')

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
url= 'http://192.168.1.94/cam-hi.jpg'

h = 650
w = 1500
frameArea = h * w
areaTH = frameArea / 250
print('Area Threshold', areaTH)

# Input/output lines
line_up = int(1.5 * (h / 5))
line_down = int(2 * (h / 5))

up_limit = int(1 * (h / 5))
down_limit = int(2.5 * (h / 5))

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
            results = Model(frame)

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


@app.route('/')
def index():
    return render_template('passenger.html')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '_main_':
    app.run(port=8000, debug=True)