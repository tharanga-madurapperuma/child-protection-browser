from ultralytics import YOLO
import cv2

# Load your trained model
model = YOLO("best.pt")

# Run inference
results = model("image4.jpeg")

# Correct way: display using OpenCV
import matplotlib.pyplot as plt

img_with_boxes = results[0].plot()
plt.imshow(img_with_boxes[..., ::-1])  # Convert BGR to RGB
plt.title("Detections")
plt.axis("off")
plt.show()

# ✅ Save with custom name using OpenCV
cv2.imwrite("weaponsNEWNEWNEW.jpg", results[0].plot())

# from gradio_client import Client

# client = Client("Rerandaka/Child_protection_API")
# result = client.predict(
# 		text="fuck my ass",
# 		api_name="//classify"
# )
# print(result)

# import requests
# import json

# def test_different_endpoints():
#     base_url = "https://rerandeka-child-protection-api.hf.space"
    
#     # Common Gradio API endpoints to try
#     endpoints_to_try = [
#         "/api/predict",
#         "/run/classify",
#         "/api/classify",
#         "/predict",
#         "/classify"
#     ]
    
#     test_data = {
#         "data": ["test message"]
#     }
    
#     for endpoint in endpoints_to_try:
#         url = base_url + endpoint
#         print(f"\nTrying: {url}")
        
#         try:
#             # Try POST request
#             response = requests.post(url, json=test_data, timeout=30)
#             print(f"POST Status: {response.status_code}")
#             if response.status_code != 404:
#                 print(f"Response: {response.text[:200]}")
                
#         except Exception as e:
#             print(f"POST Error: {e}")
        
#         try:
#             # Try GET request
#             response = requests.get(url, timeout=30)
#             print(f"GET Status: {response.status_code}")
#             if response.status_code != 404:
#                 print(f"Response: {response.text[:200]}")
                
#         except Exception as e:
#             print(f"GET Error: {e}")

# # Run the test
# test_different_endpoints()