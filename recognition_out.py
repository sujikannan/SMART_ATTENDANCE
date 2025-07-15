import cv2
import os
import pickle
import time
from datetime import datetime
import speech_recognition as sr
import pyttsx3
from insightface.app import FaceAnalysis
from utils.db_utils import record_attendance, get_employee
from utils.db_utils import initialize_db

# Initialize database before starting
initialize_db()

# Initialize components
app = FaceAnalysis(name='buffalo_sc')
app.prepare(ctx_id=0)
engine = pyttsx3.init()
recognizer = sr.Recognizer()
microphone = sr.Microphone()

def load_embeddings():
    with open("embeddings/embeddings.pkl", "rb") as f:
        return pickle.load(f)

def compare_faces(embedding1, embedding2, threshold=0.6):
    from numpy import dot
    from numpy.linalg import norm
    cosine = dot(embedding1, embedding2)/(norm(embedding1)*norm(embedding2))
    return cosine > threshold

def capture_permission_reason():
    """Capture permission reason via speech recognition"""
    engine.say("Please tell me your reason for leaving early")
    engine.runAndWait()
    
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source, timeout=10)
    
    try:
        reason = recognizer.recognize_google(audio)
        engine.say(f"Your reason is: {reason}. Is this correct?")
        engine.runAndWait()
        
        # Wait for confirmation (simple yes/no)
        with microphone as source:
            audio = recognizer.listen(source, timeout=5)
        confirmation = recognizer.recognize_google(audio).lower()
        
        if 'yes' in confirmation:
            return reason
        else:
            engine.say("Let's try again")
            engine.runAndWait()
            return capture_permission_reason()
            
    except Exception as e:
        print("Speech recognition error:", e)
        engine.say("Sorry, I didn't catch that. Please try again")
        engine.runAndWait()
        return capture_permission_reason()

def recognize_and_record_exit():
    embeddings_db = load_embeddings()
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        print("Failed to open camera.")
        return

    print("Camera started. Scanning for recognized faces...")
    permission_mode = False

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        # Check for permission button press (simulated with 'p' key)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('p'):
            permission_mode = True
            engine.say("Permission mode activated")
            engine.runAndWait()

        faces = app.get(frame)
        if faces:
            face = faces[0]
            current_embedding = face.normed_embedding
            
            for entry in embeddings_db:
                if compare_faces(current_embedding, entry['embedding']):
                    emp_id = entry['id']
                    name = entry['name']
                    current_time = datetime.now()
                    time_str = current_time.strftime("%H:%M:%S")
                    
                    # Check if leaving before 8pm or during break/lunch times
                    if (current_time.time() < datetime.strptime("20:00", "%H:%M").time() or
                        (datetime.strptime("9:10", "%H:%M").time() <= current_time.time() <= datetime.strptime("10:29", "%H:%M").time()) or
                        (datetime.strptime("10:30", "%H:%M").time() <= current_time.time() <= datetime.strptime("10:50", "%H:%M").time()) or
                        (datetime.strptime("13:00", "%H:%M").time() <= current_time.time() <= datetime.strptime("14:00", "%H:%M").time()) or
                        (datetime.strptime("16:00", "%H:%M").time() <= current_time.time() <= datetime.strptime("17:00", "%H:%M").time())):
                        
                        if permission_mode:
                            reason = capture_permission_reason()
                            record_attendance(
                                emp_id=emp_id,
                                exit_time=time_str,
                                permission_reason=reason
                            )
                            engine.say(f"Permission recorded. Goodbye {name}")
                            engine.runAndWait()
                        else:
                            engine.say(f"{name}, please use permission button or you'll be marked as absent")
                            engine.runAndWait()
                            # Wait for 5 minutes (simplified here)
                            time.sleep(5)
                            # Check if still detected (simplified)
                            engine.say(f"{name} marked as absent")
                            engine.runAndWait()
                            record_attendance(
                                emp_id=emp_id,
                                status="absent"
                            )
                    else:
                        # Normal exit recording
                        record_attendance(
                            emp_id=emp_id,
                            exit_time=time_str
                        )
                        engine.say(f"Goodbye {name}")
                        engine.runAndWait()
                    
                    # Display exit info
                    cv2.putText(frame, f"{name} - Exit recorded", (50, 50),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    cv2.imshow("Recognition", frame)
                    cv2.waitKey(3000)
                    break

        cv2.imshow("Camera", frame)
        if key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    recognize_and_record_exit()