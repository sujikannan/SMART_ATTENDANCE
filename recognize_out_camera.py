# recognize_out_camera.py
import cv2
import pickle
import numpy as np
from datetime import datetime
import pyttsx3
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
seen_exit = {}
lunch_status = {}
break_status = {}
permission_logged = set()

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
            print("Reason captured:", reason)
            return reason
        except:
            return "Could not understand"

def is_permission_time(hour, minute):
    return ((hour == 9 and minute >= 30) or (hour == 10 and minute <= 30)) or \
           (hour == 14 or (hour == 15 or (hour == 16 and minute <= 20))) or \
           (17 <= hour <= 20)

def recognize_exit():
    cap = cv2.VideoCapture(0)

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
                    time_str = now.strftime("%I:%M %p")
                    hour, minute = now.hour, now.minute

                    if emp_id not in seen_exit:
                        seen_exit[emp_id] = now

                        # Check permission time
                        if is_permission_time(hour, minute) and emp_id not in permission_logged:
                            say(f"{name}, you're leaving during permission hours.")
                            reason = capture_audio_reason()
                            say("Permission recorded.")
                            log_permission(emp_id, name, reason, time_str)
                            permission_logged.add(emp_id)

                        # Lunch return
                        elif hour == 14:
                            say(f"{name}, returned from lunch at {time_str}")

                        # Break return
                        elif hour == 17:
                            say(f"{name}, returned from break at {time_str}")

                        # General exit
                        else:
                            say(f"Goodbye {name}, logged out at {time_str}")
                            log_attendance(emp_id, name, "Present", "", time_str, "")

                    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 100, 0), 2)
                    cv2.putText(frame, f"{name} - OUT", (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 100, 0), 2)
                    break

        cv2.imshow("Out Camera - Exit", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    recognize_exit()
