# AURA Guard

AURA Guard is a Python desktop application for face recognition and liveness-based access control.

## Recognition Engine

The active engine is:

```text
FaceLogin-Dlib
```

It uses:

- `dlib.get_frontal_face_detector()` for face detection inside the recognition engine
- `face_recognition_models.face_recognition_model_location()` for the dlib recognition model
- `dlib.face_recognition_model_v1(...)` for 128-dimensional face descriptors
- Euclidean distance matching with the same core decision idea as the attached FaceLoginSystem

## Main Features

- Admin login and control panel
- User registration with guided 20+ sample face capture
- Registration Requests for unknown users
- Admin approval with fresh 20+ sample capture before creating the user
- Registered user face verification using FaceLogin-Dlib descriptors
- Multiple-frame identity confirmation before liveness starts
- Liveness test before access is granted
- Final identity re-check after liveness before approval
- Unknown user detection and snapshot capture
- Access logs, unknown alerts, liveness-failed records, and CSV reports
- SQLite local storage with safe schema migration
- CustomTkinter graphical interface

## How to Run

Open the project in PyCharm and run:

```text
main.py
```

Recommended Python version:

```text
Python 3.10 or Python 3.11, 64-bit, from python.org
```

## Important Workflow

1. The user chooses either Admin Login or Verify as Registered User.
2. The admin can register users, manage records, view logs, review registration requests, and export reports.
3. User registration captures multiple face samples and stores FaceLogin-Dlib embeddings.
4. A registered user scans their face from the verification screen.
5. The system compares the live FaceLogin-Dlib encoding with stored FaceLogin-Dlib encodings.
6. A face is accepted only after repeated stable identity matches.
7. If the face is matched, the liveness test starts.
8. Before granting access, the system performs one final identity re-check on the live face.
9. If the face is unknown, the system records the attempt and allows the person to submit a registration review request.
10. If the admin approves a request, the admin enters user details and captures 20+ fresh face samples before registration is completed.

## Project Structure

```text
src/
├── app.py
├── shell.py
├── camera_service.py
├── face_detector.py
├── face_quality.py
├── face_recognizer.py
├── liveness_detection.py
├── database_manager.py
├── report_generator.py
├── db/
├── recognition/
│   └── face_login_engine.py
├── screens/
└── widgets/
```

## Notes

The database is created automatically when the application starts. No registered users or sample face data are included in the first run.

## Final Recognition Rebuild Notes

This version uses one clean FaceLoginSystem recognition pipeline:

- Active recognition engine: FaceLogin dlib / face_recognition 128D descriptor.
- Registration saves clean face-crop samples instead of relying on full-frame re-detection later.
- Encoding uses the GUI/OpenCV validated face box first, then proper dlib/face_recognition fallbacks.
- Verification never accepts the closest user unless distance, support count and stability checks pass.
- If no registered users exist, the user is reported as unknown.
- If one registered user exists, an unknown face is still rejected unless it passes the same strict threshold.
- A debug file named `embedding_debug.txt` is written inside a user sample folder if embedding generation fails.

## Important dependency note

This build does **not** import the external `face_recognition` wrapper package at runtime. The required dlib model files are bundled inside the project folder under `face_recognition_models/`, so keep that folder beside `main.py`.
