from ultralytics import YOLO
import cv2

model = YOLO("best.pt")  # Load the model once at module level

results = model.predict(source="4", show=True)

print(results)