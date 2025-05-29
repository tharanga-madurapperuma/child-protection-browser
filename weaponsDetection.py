import cv2
from ultralytics import YOLO

def process_video(input_path, output_path, model_path, confidence_threshold=0.5):
    """
    Process a video through YOLOv8 model and save the output with bounding boxes.
    
    Args:
        input_path (str): Path to the input video file
        output_path (str): Path to save the output video
        model_path (str): Path to the YOLOv8 model file (best.pt)
        confidence_threshold (float): Minimum confidence score for detection (0-1)
    """
    # Load the YOLOv8 model
    model = YOLO(model_path)
    
    # Open the video file
    cap = cv2.VideoCapture(input_path)
    
    # Get video properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Define the codec and create VideoWriter object
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    frame_count = 0
    print(f"Processing video: {input_path}")
    print(f"Resolution: {width}x{height}, FPS: {fps}, Total frames: {total_frames}")
    
    # Loop through the video frames
    while cap.isOpened():
        # Read a frame from the video
        success, frame = cap.read()
        
        if not success:
            break
        
        # Run YOLOv8 inference on the frame
        results = model(frame, conf=confidence_threshold)
        
        # Visualize the results on the frame
        annotated_frame = results[0].plot()
        
        # Write the annotated frame to the output video
        out.write(annotated_frame)
        
        frame_count += 1
        if frame_count % 50 == 0:
            print(f"Processed {frame_count}/{total_frames} frames ({frame_count/total_frames*100:.1f}%)")
    
    # Release resources
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print(f"Processing complete. Output saved to: {output_path}")

# Example usage
if __name__ == "__main__":
    input_video = "weapons/input.mp4"  # Change to your input video path
    output_video = "weapons/output.mp4"  # Change to your desired output path
    model_path = "best.pt"  # Path to your YOLOv8 model
    
    process_video(input_video, output_video, model_path)