import cv2
import pickle
import numpy as np
from datetime import datetime
import pyttsx3
import time
import speech_recognition as sr
from insightface.app import FaceAnalysis
from scipy.spatial.distance import cosine
from utils.db_3utils import log_attendance, log_permission

app = FaceAnalysis(name='buffalo_s', providers=['CPUExecutionProvider'])
app.prepare(ctx_id=-1)

with open("embeddings/embeddings.pkl", "rb") as f:
    known_faces = pickle.load(f)
# day1
engine = pyttsx3.init()
recognizer = sr.Recognizer()
seen_ids = {}

def preprocess_image(frame):
    # Convert to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # Apply histogram equalization
    gray = cv2.equalizeHist(gray)
    # Apply bilateral filter for noise reduction while preserving edges
    filtered = cv2.bilateralFilter(gray, 9, 75, 75)
    # Convert back to color for display
    return cv2.cvtColor(filtered, cv2.COLOR_GRAY2BGR)

def say(text):
    engine.say(text)
    engine.runAndWait()

def capture_audio_reason():
    with sr.Microphone() as source:
        say("Please state your reason.")
        print("Listening...")
        audio = recognizer.listen(source, timeout=5)
        try:
            reason = recognizer.recognize_google(audio)
            print("Recognized:", reason)
            return reason
        except:
            return "Could not understand"

def is_break_time(hour, minute):
    # Morning break: 10:30 AM to 11:00 AM (10 minutes max)
    is_morning_break = (hour == 10 and 30 <= minute <= 59)
    # Evening break: 4:30 PM to 5:00 PM (10 minutes max)
    is_evening_break = (hour == 16 and 30 <= minute <= 59)
    return is_morning_break or is_evening_break

def recognize_entry():
    cap = cv2.VideoCapture(0)
    permission_logged = set()

    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            break

        # Preprocess the frame
        processed_frame = preprocess_image(frame)
        
        faces = app.get(processed_frame)

        for face in faces:
            emb = face['embedding']
            x1, y1, x2, y2 = map(int, face['bbox'])

            for data in known_faces:
                dist = cosine(emb, data['embedding'])
                if dist < 0.45:
                    emp_id, name = data['id'], data['name']
                    now = datetime.now()
                    hour, minute = now.hour, now.minute
                    time_str = now.strftime("%I:%M %p")

                    if emp_id not in seen_ids:
                        seen_ids[emp_id] = now
                        if hour < 9 or (hour == 9 and minute <= 10):
                            status, late = "Present", "No"
                            say(f"{name}, Good morning. Marked present at {time_str}")
                        else:
                            status, late = "Present", "Yes"
                            delay = (hour - 9) * 60 + minute
                            say(f"{name}, you are late by {delay} minutes")

                        log_attendance(emp_id, name, status, time_str, "", late)

                    # Check for break time
                    if is_break_time(hour, minute) and emp_id not in permission_logged:
                        cv2.rectangle(frame, (x1, y2 + 10), (x1 + 200, y2 + 50), (50, 200, 255), -1)
                        cv2.putText(frame, "Press R for Break", (x1 + 5, y2 + 40), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

                        if cv2.waitKey(1) & 0xFF == ord('r'):
                            reason = "Break time"
                            say("Break recorded.")
                            log_permission(emp_id, name, "Break", reason, time_str)
                            permission_logged.add(emp_id)

                    # Display overlay and bounding box
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, name, (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    break

        now_clock = datetime.now().strftime("%H:%M:%S")
        cv2.putText(frame, now_clock, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

        cv2.imshow("In Camera - Entry with Reason Button", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    recognize_entry()