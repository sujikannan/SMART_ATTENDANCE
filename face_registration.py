import os
import PIL.Image
import cv2
import uuid
import pickle
import sqlite3
import time
from insightface.app import FaceAnalysis
from utils.db_utils import insert_employee
from utils.db_utils import initialize_db
import PIL

# Initialize database before starting
initialize_db()

# Initialize face analysis
app = FaceAnalysis(name='buffalo_sc', providers=['CPUExecutionProvider'])
app.prepare(ctx_id=-1)

def capture_and_register():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        print("Failed to open camera.")
        return

    print("Camera started. Scanning for face...")

    emp_id = input("Enter Employee ID (manual): ")
    name = input("Enter Name: ")
    role = input("Enter Role: ")
    team = input("Enter Team Name: ")  # New input field for team

    os.makedirs(f"images/{emp_id}", exist_ok=True)
    os.makedirs("embeddings", exist_ok=True)

    accepted_images = []
    embeddings_data = []

    count = 0
    while count < 3:
        print(f"Preparing to capture image {count + 1}. Look at the camera.")

        start_time = time.time()
        while time.time() - start_time < 3:
            ret, frame = cap.read()
            if not ret:
                continue

            timer = 3 - int(time.time() - start_time)
            temp_frame = frame.copy()
            cv2.putText(temp_frame, f"Capturing in {timer}s", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            cv2.imshow("Camera", temp_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("Exit requested.")
                cap.release()
                cv2.destroyAllWindows()
                return

        ret, frame = cap.read()
        if not ret:
            print("Frame capture failed.")
            continue

        faces = app.get(frame)
        if faces:
            face = faces[0]
            emb = face['embedding']

            preview = frame.copy()
            cv2.putText(preview, f"Image {count + 1}: Press 'y' to accept", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow("Camera", preview)
            print("Press 'y' to accept image, or any other key to skip.")
            key = cv2.waitKey(5000)

            if key == ord('y'):
                img_path = f"images/{emp_id}/{uuid.uuid4().hex}.jpg"
                # img = PIL.Image.open(img_path)
                cv2.imwrite(img_path, frame)
                accepted_images.append(img_path)
                embeddings_data.append({
                    'id': emp_id,
                    'name': name,
                    'role': role,
                    'team': team,  # Added team to embeddings
                    'embedding': emb,
                    'profile_image':preview
                })
                print(f"Accepted image {count + 1}")
                count += 1
            else:
                print("Skipped image.")
        else:
            print("No face detected. Retrying...")

    if accepted_images:
        if os.path.exists("embeddings/embeddings.pkl"):
            with open("embeddings/embeddings.pkl", "rb") as f:
                db = pickle.load(f)
        else:
            db = []

        db.extend(embeddings_data)

        with open("embeddings/embeddings.pkl", "wb") as f:
            pickle.dump(db, f)

        insert_employee(emp_id, name, role, team, accepted_images[0])  # Updated to include team
        print(f"{name} registered successfully with {len(accepted_images)} confirmed images.")

        print("Previewing accepted images...")
        for i, img_path in enumerate(accepted_images):
            img = cv2.imread(img_path)
            if img is not None:
                cv2.imshow(f"Accepted Image {i+1}", img)
                key = cv2.waitKey(2000)  # Show each image for 2 seconds
                cv2.destroyWindow(f"Accepted Image {i+1}")
                if key == ord('q'):
                    print("Preview skipped by user.")
                    break
    else:
        print("No confirmed images. Registration aborted.")

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    capture_and_register()