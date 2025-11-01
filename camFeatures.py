"""
Camera Features Module for MARVIN AI Assistant
Provides face detection, hand tracking, scene description, and facial expression analysis
"""

import sys
import os
from contextlib import redirect_stderr
import io

# Suppress cv2 warnings during import
f = io.StringIO()
with redirect_stderr(f):
    import cv2
    from cvzone.FaceDetectionModule import FaceDetector
    from cvzone.HandTrackingModule import HandDetector

import platform
import time
import subprocess
import openai
import numpy as np
from typing import Optional, Tuple
import base64

# Restore normal stderr
sys.stderr = sys.__stderr__

# Suppress TensorFlow and OpenCV C++ logs
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "5"
try:
    cv2.utils.logging.setLogLevel(cv2.LOG_LEVEL_ERROR)
except AttributeError:
    pass

# ========== Configuration Constants ==========
CAMERA_WARMUP_SECONDS = 3
SNAPSHOT_WARMUP_SECONDS = 3
FACE_DETECTION_CONFIDENCE = 0.7
HAND_DETECTION_CONFIDENCE = 0.7
MAX_HANDS = 2
REAL_HAND_WIDTH = 8  # cm, average adult hand width
FOCAL_LENGTH = 700   # pixels, adjust after calibration
HAND_DISTANCE_MULTIPLIER = 4

# ========== Global Variables ==========
camera_active = False

# ========== Detector Initialization ==========
face_detector = FaceDetector(minDetectionCon=FACE_DETECTION_CONFIDENCE)
hand_detectors = [HandDetector(maxHands=MAX_HANDS), HandDetector(maxHands=MAX_HANDS)]


def open_camera(index: int = 0) -> None:
    """
    Open camera feed with face and hand detection overlays.
    
    Args:
        index (int): Camera index to use. Defaults to 0 (primary camera).
    """
    cap = cv2.VideoCapture(index)

    if not cap.isOpened():
        print(f"❌ Cannot open camera {index}")
        return

    # Use local detectors for this camera session
    local_face_detector = FaceDetector(minDetectionCon=FACE_DETECTION_CONFIDENCE)
    local_hand_detector = HandDetector(detectionCon=HAND_DETECTION_CONFIDENCE, maxHands=MAX_HANDS)

    print(f"🎥 Camera {index} active — press 'q' to quit window")

    while True:
        success, img = cap.read()

        # Guard: if no frame, skip loop iteration
        if not success or img is None:
            print(f"⚠️ Failed to grab frame from cam {index}")
            continue

        # Detect faces and draw bounding boxes
        img, bboxs = local_face_detector.findFaces(img)
        if bboxs:
            for bbox in bboxs:
                x, y, w, h = bbox["bbox"]
                cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)  # Green

        # Detect hands and draw distance estimates
        hands, img = local_hand_detector.findHands(img)
        if hands:
            for hand in hands:
                x, y, w, h = hand['bbox']
                cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                
                # Estimate distance based on hand width
                distance_cm = (REAL_HAND_WIDTH * FOCAL_LENGTH * HAND_DISTANCE_MULTIPLIER) / w
                cv2.putText(
                    img, f"Hand Dist: {distance_cm:.1f}cm",
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2
                )

        # Display frame
        cv2.imshow(f"Camera {index}", img)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


def compare_cameras() -> None:
    """
    Display two camera feeds side-by-side with face similarity comparison.
    
    Uses ORB feature matching to compare faces detected in both camera feeds
    and displays a similarity score overlay.
    """
    caps = [cv2.VideoCapture(0), cv2.VideoCapture(1)]
    
    # Create ORB detector and BruteForce matcher for face comparison
    orb = cv2.ORB_create()
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

    print("🎥 Comparing cameras — press 'q' to quit")

    while True:
        frames = []
        face_images = []

        for i, cap in enumerate(caps):
            ret, frame = cap.read()
            if not ret:
                # Use blank frame if camera read fails
                frame = np.zeros((480, 640, 3), dtype=np.uint8)

            # Detect faces in current frame
            frame, bboxs = face_detector.findFaces(frame, draw=True)

            # Detect hands using the corresponding hand detector for this camera
            hands, frame = hand_detectors[i].findHands(frame, draw=True)

            # Display hand count for each camera
            if hands:
                cv2.putText(frame, f"Hands: {len(hands)}", (10, 70),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

            # Extract face region for ORB comparison
            face_img = None
            if bboxs:
                x, y, w, h = bboxs[0]["bbox"]
                x1, y1 = max(0, x), max(0, y)
                x2, y2 = min(frame.shape[1], x + w), min(frame.shape[0], y + h)
                face_crop = frame[y1:y2, x1:x2]
                if face_crop.size != 0:
                    face_img = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)

            face_images.append(face_img)
            frames.append(frame)

        # Compare faces between the two camera feeds using ORB
        if len(face_images) == 2 and all(f is not None for f in face_images):
            kp1, des1 = orb.detectAndCompute(face_images[0], None)
            kp2, des2 = orb.detectAndCompute(face_images[1], None)
            if des1 is not None and des2 is not None:
                matches = bf.match(des1, des2)
                matches = sorted(matches, key=lambda x: x.distance)
                similarity = len(matches) / min(len(kp1), len(kp2)) if min(len(kp1), len(kp2)) > 0 else 0
                cv2.putText(frames[0], f"Similarity: {similarity:.2f}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # Display both feeds side by side
        combined = np.hstack(frames)
        cv2.imshow("Compare Cameras", combined)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    for cap in caps:
        cap.release()
    cv2.destroyAllWindows()


def quit_camera() -> None:
    """
    Stop the active camera loop and close camera windows.
    """
    global camera_active
    if not camera_active:
        print("Camera is not running.")
        return
    camera_active = False
    cv2.destroyAllWindows()
    print("Camera closed.")


def take_snapshot(filename: str = "snapshot.jpg") -> None:
    """
    Capture a snapshot from the camera with warmup period and auto-open.
    
    Args:
        filename (str): Path where snapshot will be saved. Defaults to 'snapshot.jpg'.
    """
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Could not open camera for snapshot.")
        return
    
    print(f"⏳ Preparing camera... hold still for {SNAPSHOT_WARMUP_SECONDS} seconds.")
    
    # Warm-up frames: discard initial frames while camera adjusts autoexposure
    start_time = time.time()
    while time.time() - start_time < SNAPSHOT_WARMUP_SECONDS:
        cap.read()  # Read and discard frames
    
    # Capture the actual snapshot
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(filename, frame)
        print(f"📸 Snapshot saved as {filename}")

        # Auto-open the saved photo using OS-specific commands
        if platform.system() == "Darwin":
            subprocess.run(["open", filename])
        elif platform.system() == "Windows":
            os.startfile(filename)
        else:
            subprocess.run(["xdg-open", filename])
    else:
        print("⚠️ Failed to capture frame.")

    cap.release()


def take_frame(cam_index: int = 0) -> Optional[np.ndarray]:
    """
    Capture a single frame from the specified camera.
    
    Args:
        cam_index (int): Camera index to use. Defaults to 0 (primary camera).
        
    Returns:
        np.ndarray: Captured frame as numpy array, or None if capture failed.
    """
    cap = cv2.VideoCapture(cam_index)
    if not cap.isOpened():
        print("❌ Cannot open camera")
        return None
    ret, frame = cap.read()
    cap.release()
    if ret:
        return frame
    return None


def describe_scene() -> str:
    """
    Capture a frame and use OpenAI Vision API to describe what's in the scene.
    
    Returns:
        str: Description of the scene, or error message if failed.
    """
    frame = take_frame()
    if frame is None:
        return "I couldn't capture an image."

    filename = "snapshot_temp.jpg"
    cv2.imwrite(filename, frame)

    try:
        with open(filename, "rb") as img_file:
            b64 = base64.b64encode(img_file.read()).decode()

        response = openai.chat.completions.create(
            model="gpt-4o-mini",  # Vision-capable model
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe what you see in this picture in 2-3 sentences."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                ]
            }]
        )
        description = response.choices[0].message.content.strip()
        return description
    except Exception as e:
        print(f"❌ Error describing scene: {e}")
        return "I couldn't analyze the scene."
    finally:
        # Clean up temp file
        try:
            os.unlink(filename)
        except:
            pass


def analyze_expression_from_camera(cam_index: int = 0) -> str:
    """
    Takes a picture from camera, detects faces, analyzes up to 3 people's facial expressions
    and provides detailed feedback using OpenAI Vision API.
    
    Args:
        cam_index (int): Camera index to use. Defaults to 0.
        
    Returns:
        str: Facial expression analysis, or error message if failed.
    """
    print("⏳ Taking snapshot for facial analysis...")
    frame = take_frame(cam_index)
    if frame is None:
        return "I couldn't access the camera."

    # Detect faces
    img, bboxs = face_detector.findFaces(frame, draw=False)
    num_faces = len(bboxs) if bboxs else 0

    filename = "expression_snapshot.jpg"
    cv2.imwrite(filename, frame)
    print(f"📸 Snapshot captured for analysis: {filename}")

    if num_faces == 0:
        print("No person detected in the frame.")
        return "I don't see any person in the frame."

    try:
        with open(filename, "rb") as img_file:
            b64 = base64.b64encode(img_file.read()).decode()

        if num_faces == 1:
            prompt = (
                "Analyze the single person's facial expression in this photo. "
                "Describe their emotion and suggest what response or action would be appropriate. "
                "Also mention anything interesting about the environment if visible."
            )
        elif 1 < num_faces <= 3:
            prompt = (
                f"There are {num_faces} people in this photo. Analyze each of their facial expressions "
                "and describe how they might be feeling. Suggest what would be an appropriate response for each, "
                "and note any visible environmental or mood context."
            )
        else:
            prompt = (
                f"There are more than three people. Give a general analysis of the group's emotional tone "
                "and energy, and describe what kind of situation this might be, including environmental cues."
            )

        response = openai.chat.completions.create(
            model="gpt-4o-mini",  # Vision + reasoning
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                ]
            }],
            max_tokens=500
        )

        analysis = response.choices[0].message.content.strip()
        return analysis
    except Exception as e:
        print(f"❌ Error analyzing facial expression: {e}")
        return "Sorry, I couldn't analyze the facial expressions."


def save_camera_snapshot(filename: str = "snapshot.jpg") -> bool:
    """
    Quickly capture and save a single snapshot from the default camera.
    
    This is a simpler, faster alternative to take_snapshot() without warmup delay.

    Args:
        filename (str): The file path/name where the snapshot will be saved.
                        Defaults to 'snapshot.jpg'.
                        
    Returns:
        bool: True if successful, False otherwise.
    """
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Cannot open camera for snapshot.")
        return False

    ret, frame = cap.read()
    cap.release()

    if ret:
        cv2.imwrite(filename, frame)
        print(f"📸 Snapshot saved as {filename}")
        return True
    else:
        print("❌ Failed to capture frame.")
        return False
