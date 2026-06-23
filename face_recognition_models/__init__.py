from pathlib import Path

_model_dir = Path(__file__).resolve().parent / "models"

def face_recognition_model_location():
    return str(_model_dir / "dlib_face_recognition_resnet_model_v1.dat")

def pose_predictor_five_point_model_location():
    return str(_model_dir / "shape_predictor_5_face_landmarks.dat")

def pose_predictor_model_location():
    return pose_predictor_five_point_model_location()

def cnn_face_detector_model_location():
    return str(_model_dir / "mmod_human_face_detector.dat")
