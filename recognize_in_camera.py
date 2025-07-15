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

app = FaceAnalysis(name='buffalo_sc', providers=['CPUExecutionProvider'])
app.prepare(ctx_id=0)

with open("embeddings/embeddings.pkl", "rb") as f:
    known_faces = pickle.load(f)

engine = pyttsx3.init()
recognizer = sr.Recognizer()
seen_ids = {}

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

def is_reason_time(hour, minute):
    
    return (hour == 8 and minute >= 10) or (8 <= hour < 0)

def is_break_time(hour, minute):
    is_morning_break=(hour == 10 and 30 <= minute <= 40) # 10:30 PM to 10:40 PM
    is_evening_break= (hour == 16 and 30 <= minute <= 40)  # 4:30 PM to 4:40 PM

def recognize_entry():
    cap = cv2.VideoCapture(0)
    permission_logged = set()

    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            break

        faces = app.get(frame)

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

                    
                    if is_reason_time(hour, minute) and not is_break_time(hour, minute) and emp_id not in permission_logged:
                        cv2.rectangle(frame, (x1, y2 + 10), (x1 + 200, y2 + 50), (50, 200, 255), -1)
                        cv2.putText(frame, "Press R for Reason", (x1 + 5, y2 + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

                        if cv2.waitKey(1) & 0xFF == ord('r'):
                            reason = capture_audio_reason()
                            say("Permission recorded.")
                            log_permission(emp_id, name, reason, time_str)
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
