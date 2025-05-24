from ultralytics import YOLO

# Load model using the correct path
model = YOLO("best.pt")


# Run inference
results = model("D:\Programming\Python\child-protection-browser\image1.jpeg")  # or replace with your image filename

# Display result
results[0].show()  # Built-in viewer

# OR use OpenCV + matplotlib
# import cv2
# from matplotlib import pyplot as plt

# res_img = results[0].plot()
# plt.imshow(cv2.cvtColor(res_img, cv2.COLOR_BGR2RGB))
# plt.axis('off')
# plt.show()


# from ultralytics import YOLO
# import cv2

# # Load the model
# model = YOLO("best.pt")

# video_path = "input_video.mp4"
# cap = cv2.VideoCapture(video_path)

# # Get video properties
# original_fps = cap.get(cv2.CAP_PROP_FPS)
# frame_interval = int(original_fps)  # e.g., skip 30 frames if original FPS is 30
# width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
# height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

# # Set your custom FPS for output
# output_fps = 5
# out = cv2.VideoWriter("output_video.mp4", cv2.VideoWriter_fourcc(*'mp4v'), output_fps, (width, height))

# frame_count = 0

# while cap.isOpened():
#     ret, frame = cap.read()
#     if not ret:
#         break

#     # Process only every Nth frame
#     if frame_count % frame_interval == 0:
#         results = model(frame)
#         annotated_frame = results[0].plot()
#         out.write(annotated_frame)

#     frame_count += 1

# cap.release()
# out.release()
# cv2.destroyAllWindows()
