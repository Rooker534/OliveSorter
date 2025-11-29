import os
import time
import cv2
import numpy as np
import serial
from tkinter import Tk, Button, Label
from edge_impulse_linux.image import ImageImpulseRunner
from PIL import Image, ImageTk

# =========================
# Configuration
# =========================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(SCRIPT_DIR, "OliveSortingLib.eim")

CAMERA_INDEX = 0

# Serial port for ESP32 / Arduino
SERIAL_PORT = "/dev/ttyACM1"   # adjust if needed (e.g. /dev/ttyACM0)
SERIAL_BAUD = 115200

runner = None
cam = None
ser = None

root = None
label_tl = None
label_tr = None
label_bl = None
label_br = None
status_label = None

# Edge Impulse labels
GOOD_LABEL = "GoodOlives"
BAD_LABEL  = "BadOlives"

# =========================
# Serial helpers
# =========================

def setup_serial():
    global ser
    ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1)
    time.sleep(2)  # allow ESP32 to reset
    print("Serial opened on", SERIAL_PORT)

def send_command(cmd):
    """
    Send a text command over serial, e.g. 'D' or 'S 1 0 1 0'
    """
    if ser is None or not ser.is_open:
        print("Serial not open, cannot send:", cmd)
        return
    line = (cmd + "\n").encode("utf-8")
    ser.write(line)
    ser.flush()
    print("Sent:", repr(cmd))

# =========================
# Edge Impulse
# =========================

def load_model():
    global runner
    runner = ImageImpulseRunner(MODEL_PATH)
    info = runner.init()
    print("Loaded model:", info["project"]["name"])
    print("Labels:", info["model_parameters"]["labels"])
    return info

def classify_one_pil(img_pil):
    img_np = np.array(img_pil)  # RGB
    features, _ = runner.get_features_from_image(img_np)
    res = runner.classify(features)
    if "classification" in res["result"]:
        scores = res["result"]["classification"]
        best_label = max(scores, key=scores.get)
        best_score = scores[best_label]
        print(f"Result: {best_label} ({best_score:.2f})")
        return best_label
    else:
        print("No classification result")
        return "Unknown"

# =========================
# Main cycle
# =========================

def run_sorting_cycle():
    global cam

    print("Button clicked, running cycle...")

    # 1) Tell ESP32 to drop olives (first 4 servos)
    send_command("D")

    # 2) small wait, then warmup frames to avoid black first frame
    time.sleep(0.2)
    for i in range(10):
        ret, frame = cam.read()
        if not ret:
            status_label.config(text="Failed to capture image (warmup)!")
            return

    ret, frame = cam.read()
    print("final ret:", ret)
    if not ret or frame is None:
        status_label.config(text="Failed to capture image!")
        return

    # 3) Convert to RGB and PIL
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img_full = Image.fromarray(frame_rgb)

    # 4) Split into 4 quadrants
    width, height = img_full.size
    w2, h2 = width // 2, height // 2

    top_left  = img_full.crop((0,   0,   w2,   h2))
    top_right = img_full.crop((w2,  0,   width, h2))
    bottom_left  = img_full.crop((0,   h2, w2,   height))
    bottom_right = img_full.crop((w2,  h2, width, height))

    # 5) Show 4 images in GUI
    label_tl.img_tk = ImageTk.PhotoImage(top_left)
    label_tr.img_tk = ImageTk.PhotoImage(top_right)
    label_bl.img_tk = ImageTk.PhotoImage(bottom_left)
    label_br.img_tk = ImageTk.PhotoImage(bottom_right)

    label_tl.config(image=label_tl.img_tk)
    label_tr.config(image=label_tr.img_tk)
    label_bl.config(image=label_bl.img_tk)
    label_br.config(image=label_br.img_tk)

    status_label.config(text="Snapshot split into 4 parts.")

    # 6) Classify each crop separately
    crops_pil = [top_left, top_right, bottom_left, bottom_right]
    results = []
    for i, crop in enumerate(crops_pil):
        print(f"Classifying olive {i+1} ...")
        label = classify_one_pil(crop)
        results.append(label)

    print("All 4 results:", results)

    # 7) Build sort pattern for ESP32 (1 = good, 0 = bad)
    pattern_bits = []
    for lbl in results:
        if lbl == GOOD_LABEL:
            pattern_bits.append("1")
        else:
            pattern_bits.append("0")

    # command example: S 1 0 1 0
    cmd = "S " + " ".join(pattern_bits)
    print("Sending sort command:", cmd)
    send_command(cmd)

def on_button_click():
    try:
        run_sorting_cycle()
    except Exception as e:
        print("Error during sorting cycle:", e)
        status_label.config(text=f"Error: {e}")

def on_close():
    global cam, ser
    if cam is not None:
        cam.release()
    if runner is not None:
        runner.stop()
    if ser is not None and ser.is_open:
        ser.close()
    root.destroy()

# =========================
# Main
# =========================

def main():
    global root, label_tl, label_tr, label_bl, label_br, status_label, cam

    try:
        load_model()
        setup_serial()

        cam = cv2.VideoCapture(CAMERA_INDEX)
        cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        print("Camera opened:", cam.isOpened())

        root = Tk()
        root.title("Olive Sorter 2x2")

        label_tl = Label(root)
        label_tr = Label(root)
        label_bl = Label(root)
        label_br = Label(root)

        label_tl.grid(row=0, column=0, padx=5, pady=5)
        label_tr.grid(row=0, column=1, padx=5, pady=5)
        label_bl.grid(row=1, column=0, padx=5, pady=5)
        label_br.grid(row=1, column=1, padx=5, pady=5)

        status_label = Label(root, text="", font=("Arial", 12))
        status_label.grid(row=2, column=0, columnspan=2, pady=10)

        btn = Button(root, text="Sort Olives", command=on_button_click, font=("Arial", 14))
        btn.grid(row=3, column=0, columnspan=2, pady=10)

        root.protocol("WM_DELETE_WINDOW", on_close)
        root.mainloop()

    finally:
        if cam is not None:
            cam.release()
        if runner is not None:
            runner.stop()
        if ser is not None and ser.is_open:
            ser.close()

if __name__ == "__main__":
    main()