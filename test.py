from ultralytics import YOLO
import cv2
import matplotlib.pyplot as plt

# Load your trained model
model = YOLO("best.pt")

# List of images
images = ["testImages/image1.webp", "testImages/image2.jpg", "testImages/image4.jpeg"]

for i, img_path in enumerate(images):
    # Run inference
    results = model(img_path)

    # Get image with boxes
    img_with_boxes = results[0].plot()

    # Show each image in a separate OpenCV window
    window_name = f"Detections {i+1}"
    cv2.imshow(window_name, img_with_boxes)

    # Save output with unique name
    cv2.imwrite(f"output_{i+1}.jpg", img_with_boxes)

# Wait until a key is pressed, then close all windows
cv2.waitKey(0)
cv2.destroyAllWindows()


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