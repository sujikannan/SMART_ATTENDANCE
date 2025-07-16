import cv2
import pickle
import numpy as np
from datetime import datetime
import pyttsx3
import speech_recognition as sr
from insightface.app import FaceAnalysis
from scipy.spatial.distance import cosine
from utils.db_3utils import log_attendance, log_permission
from utils.db_utils import record_attendance, get_employee

app = FaceAnalysis(name='buffalo_s', providers=['CPUExecutionProvider'])
app.prepare(ctx_id=-1)

with open("embeddings/embeddings.pkl", "rb") as f:
    known_faces = pickle.load(f)

engine = pyttsx3.init()
recognizer = sr.Recognizer()
seen_exit = {}
permission_logged = set()

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
            print("Reason captured:", reason)
            return reason
        except:
            return "Could not understand"

def recognize_exit():
    cap = cv2.VideoCapture(2)
    permission_requested = False
    current_emp_id = None
    current_name = None
    current_face_coords = None

    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            break

        # Preprocess the frame
        processed_frame = preprocess_image(frame)
        
        faces = app.get(processed_frame)

        # Reset permission state if no face detected
        if not faces:
            permission_requested = False
            current_emp_id = None
            current_name = None
            current_face_coords = None

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
                    today = now.strftime('%Y-%m-%d')

                    # Store current face info for permission request
                    current_emp_id = emp_id
                    current_name = name
                    current_face_coords = (x1, y1, x2, y2)

                    # Display permission button (always visible)
                    cv2.rectangle(frame, (x1, y2 + 10), (x1 + 200, y2 + 50), (50, 200, 255), -1)
                    cv2.putText(frame, "Press P for Permission", (x1 + 5, y2 + 40), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

                    # Check if this is a re-entry after exit
                    employee = get_employee(emp_id)
                    if employee:
                        if hour >= 20:  # After 8 PM
                            # Update exit time if this is a re-entry
                            record_attendance(
                                emp_id=emp_id,
                                exit_time=time_str,
                                status="Present"
                            )
                            say(f"Updated exit time for {name} to {time_str}")
                        else:
                            if emp_id not in seen_exit:
                                seen_exit[emp_id] = now
                                say(f"Goodbye {name}, logged out at {time_str}")
                                log_attendance(emp_id, name, "Present", "", time_str, "")

                        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 100, 0), 2)
                        cv2.putText(frame, f"{name} - OUT", (x1, y1 - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 100, 0), 2)
                        break

        # Check for permission key press ('p')
        key = cv2.waitKey(1)
        if key == ord('p') and current_emp_id and current_name and current_face_coords:
            x1, y1, x2, y2 = current_face_coords
            permission_requested = True
            cv2.rectangle(frame, (x1, y2 + 10), (x1 + 200, y2 + 50), (0, 255, 0), -1)
            cv2.putText(frame, "Recording Permission...", (x1 + 5, y2 + 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
            cv2.imshow("Out Camera - Exit", frame)
            cv2.waitKey(100)
            
            reason = capture_audio_reason()
            say("Permission recorded.")
            log_permission(current_emp_id, current_name, "Permission", reason, time_str)
            permission_logged.add(current_emp_id)
            permission_requested = False

        cv2.imshow("Out Camera - Exit", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    recognize_exit()