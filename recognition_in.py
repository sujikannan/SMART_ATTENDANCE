import cv2
import os
import pickle
import time
from datetime import datetime
import pyttsx3
from insightface.app import FaceAnalysis
from utils.db_utils import record_attendance, get_employee
from utils.db_utils import initialize_db

# Initialize database before starting
initialize_db()

# Initialize face analysis and speech engine
app = FaceAnalysis(name='buffalo_sc')
app.prepare(ctx_id=-1)
engine = pyttsx3.init()

# Load embeddings
def load_embeddings():
    with open("embeddings/embeddings.pkl", "rb") as f:
        return pickle.load(f)

# Compare faces using cosine similarity
def compare_faces(embedding1, embedding2, threshold=0.6):
    from numpy import dot
    from numpy.linalg import norm
    cosine = dot(embedding1, embedding2)/(norm(embedding1)*norm(embedding2))
    return cosine > threshold

def recognize_and_mark_attendance():
    embeddings_db = load_embeddings()
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        print("Failed to open camera.")
        return

    print("Camera started. Scanning for recognized faces...")
    recognized_ids = set()

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        faces = app.get(frame)
        if faces:
            face = faces[0]
            current_embedding = face.normed_embedding
            
            for entry in embeddings_db:
                if compare_faces(current_embedding, entry['embedding']):
                    emp_id = entry['id']
                    name = entry['name']
                    
                    if emp_id not in recognized_ids:
                        recognized_ids.add(emp_id)
                        current_time = datetime.now()
                        time_str = current_time.strftime("%H:%M:%S")
                        date_str = current_time.strftime("%Y-%m-%d")
                        
                        # Determine status based on time
                        if current_time.time() < datetime.strptime("09:00", "%H:%M").time():
                            status = "present"
                            greeting = f"Good morning {name}"
                        elif current_time.time() < datetime.strptime("09:10", "%H:%M").time():
                            status = "present"
                            greeting = f"Good morning {name}"
                        else:
                            status = "late"
                            greeting = f"You are late {name}, current time is {time_str}"
                        
                        # Speak greeting
                        engine.say(greeting)
                        engine.runAndWait()
                        
                        # Record attendance
                        record_attendance(
                            emp_id=emp_id,
                            entry_time=time_str,
                            status=status
                        )
                        
                        print(f"Recognized: {name} ({emp_id}) - Marked as {status}")
                        
                        # Display recognition info
                        cv2.putText(frame, f"{name} - {status}", (50, 50),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                        cv2.imshow("Recognition", frame)
                        cv2.waitKey(3000)  # Show for 3 seconds
                        break

        cv2.imshow("Camera", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    recognize_and_mark_attendance()