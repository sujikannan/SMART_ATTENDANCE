import multiprocessing
import subprocess

def run_in_camera():
    subprocess.run(["python3", "recognize_in_camera.py"])

def run_out_camera():
    subprocess.run(["python3", "recognize_out_camera.py"])

if __name__ == "__main__":
    p1 = multiprocessing.Process(target=run_in_camera)
    p2 = multiprocessing.Process(target=run_out_camera)

    p1.start()
    p2.start()

    p1.join()
    p2.join()
