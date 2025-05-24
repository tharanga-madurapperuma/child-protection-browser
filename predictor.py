# predictor.py

from ultralytics import YOLO

# Load once at module level
model = YOLO("best.pt")  # Path to your YOLOv8 model

def detect_inappropriate_content(image_path):
    results = model(image_path)

    detected_labels = []
    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            label = r.names[cls_id]
            detected_labels.append(label)

    # Define "bad" classes
    bad_classes = {"porn", "blood", "alcohol", "violation"}
    found = bad_classes.intersection(set(detected_labels))

    return list(found)  # return list of matched classes
