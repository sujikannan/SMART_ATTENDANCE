import os
import cv2
import uuid
import pickle
import time
from insightface.app import FaceAnalysis
from utils.db_utils import insert_employee
from utils.db_utils import initialize_db
initialize_db()
app = FaceAnalysis(name='buffalo_sc', providers=['CPUExecutionProvider'])
app.prepare(ctx_id=-1)
def capture_and_register():
    video_path = input("Enter the path to the video file: ")
    cap = cv2.VideoCapture('sample.mp4')
    
    if not cap.isOpened():
        print(f"Failed to open video file: {video_path}")
        return

    print(f"Video opened successfully: {video_path}")

    emp_id = input("Enter Employee ID (manual): ")
    name = input("Enter Name: ")
    role = input("Enter Role: ")
    team = input("Enter Team Name: ")

    os.makedirs(f"images/{emp_id}", exist_ok=True)
    os.makedirs("embeddings", exist_ok=True)

    accepted_images = []
    embeddings_data = []

    count = 0
    frame_count = 0
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_interval = int(fps)  # Process 1 frame per second
    while count < 3 and cap.isOpened():
        ret, frame = cap.read()
        frame_count += 1
        
        if not ret:
            print("End of video reached.")
            break
            
        # Skip frames to process about 1 frame per second
        if frame_count % frame_interval != 0:
            continue

        print(f"Processing frame {frame_count}...")

        faces = app.get(frame)
        if faces:
            face = faces[0]
            emb = face['embedding']

            preview = frame.copy()
            cv2.putText(preview, f"Image {count + 1}: Press 'y' to accept", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow("Video Frame", preview)
            print("Press 'y' to accept image, 'n' to skip, or 'q' to quit.")
            key = cv2.waitKey(0)  # Wait indefinitely for user input

            if key == ord('y'):
                img_path = f"images/{emp_id}/{uuid.uuid4().hex}.jpg"
                cv2.imwrite(img_path, frame)
                accepted_images.append(img_path)
                embeddings_data.append({
                    'id': emp_id,
                    'name': name,
                    'role': role,
                    'team': team,
                    'embedding': emb
                })
                print(f"Accepted image {count + 1}")
                count += 1
            elif key == ord('n'):
                print("Skipped image.")
            elif key == ord('q'):
                print("Registration aborted by user.")
                break
            cv2.destroyWindow("Video Frame")
        else:
            print("No face detected in this frame. Continuing...")

    if accepted_images:
        if os.path.exists("embeddings/embeddings.pkl"):
            with open("embeddings/embeddings.pkl", "rb") as f:
                db = pickle.load(f)
        else:
            db = []

        db.extend(embeddings_data)

        with open("embeddings/embeddings.pkl", "wb") as f:
            pickle.dump(db, f)

        insert_employee(emp_id, name, role, team, accepted_images[0])
        print(f"{name} registered successfully with {len(accepted_images)} confirmed images.")

        print("Previewing accepted images...")
        for i, img_path in enumerate(accepted_images):
            img = cv2.imread(img_path)
            if img is not None:
                cv2.imshow(f"Accepted Image {i+1}", img)
                key = cv2.waitKey(2000)
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