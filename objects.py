import torch
from geoclip import GeoCLIP
import requests
import sys
import os
import json
from PIL import Image
import piexif
from ultralytics import YOLO

# Load YOLO model for object detection
def load_detection_model():
    model_path = "yolov8n.pt"  # Pre-trained YOLOv8 small model
    if not os.path.exists(model_path):
        print("Downloading YOLO model...")
        torch.hub.download_url_to_file(
            'https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt', model_path
        )
    return YOLO(model_path)

def detect_objects(image_path, model):
    """Detect objects in the image using the YOLO model."""
    results = model(image_path)  # Perform detection
    detections = []
    for result in results:  # Iterate over detected objects
        for box in result.boxes:  # Access bounding boxes
            class_id = int(box.cls.item())  # Convert class tensor to an integer
            label = result.names[class_id]  # Class name
            confidence = float(box.conf.item())  # Confidence score
            #if label in ["tank", "weapon"]:  # Filter for relevant labels
            detections.append({
                    "label": label,
                    "confidence": confidence,
                    "bbox": box.xyxy.tolist()  # Bounding box coordinates
                })
    return detections

def extract_metadata_geolocation(image_path):
    """Extract geolocation metadata from the image."""
    try:
        img = Image.open(image_path)
        exif_data = piexif.load(img.info.get("exif", b""))

        if "GPS" in exif_data and exif_data["GPS"]:
            gps_info = exif_data["GPS"]
            def convert_to_degrees(value):
                d, m, s = value
                return d + (m / 60.0) + (s / 3600.0)

            lat_ref = gps_info.get(piexif.GPSIFD.GPSLatitudeRef, b"").decode("utf-8")
            lon_ref = gps_info.get(piexif.GPSIFD.GPSLongitudeRef, b"").decode("utf-8")

            lat = convert_to_degrees(gps_info[piexif.GPSIFD.GPSLatitude])
            lon = convert_to_degrees(gps_info[piexif.GPSIFD.GPSLongitude])

            if lat_ref == "S":
                lat = -lat
            if lon_ref == "W":
                lon = -lon

            return lat, lon

    except Exception as e:
        print(f"Error extracting metadata geolocation: {e}")

    return None

def save_geo_data(output_path, image_path, additional_info, lat, lon, prob, detections):
    """Save extracted geo data to a text file."""
    try:
        with open(output_path, "a") as file:
            file.write(f"Image: {image_path}\n")
            file.write(f"Additional Info: {additional_info}\n")
            file.write(f"Latitude: {lat:.6f}\n")
            file.write(f"Longitude: {lon:.6f}\n")
            file.write(f"Probability: {prob:.6f}\n")
            file.write(f"Detections: {detections}\n")
            file.write("\n")
    except Exception as e:
        print(f"Error saving geo data: {e}")

def process_image(image_path, endpoint_url, output_path, geoclip_model, detection_model, additional_info):
    """Process a single image for geolocation extraction."""
    metadata_coords = extract_metadata_geolocation(image_path)

    if metadata_coords:
        lat, lon = metadata_coords
        print(f"Metadata Geolocation Found: Latitude={lat:.6f}, Longitude={lon:.6f}")
        prob = 1.0  # Assume confidence is 100% for metadata geolocation
    else:
        print("No metadata geolocation found. Running GeoCLIP.")
        top_pred_gps, top_pred_prob = geoclip_model.predict(image_path, top_k=1)  # Get top 1 prediction

        if top_pred_gps is None or len(top_pred_gps) == 0:
            print(f"No GPS coordinates found for the image: {image_path}")
            return

        lat_tensor, lon_tensor = top_pred_gps[0]
        prob_tensor = top_pred_prob[0]

        lat = lat_tensor.item()
        lon = lon_tensor.item()
        prob = prob_tensor.item()

    print(f"Extracted Coordinates: Latitude={lat:.6f}, Longitude={lon:.6f}, Probability={prob:.6f}")

    # Detect objects
    detections = detect_objects(image_path, detection_model)
    print(f"Detections: {detections}")

    # Save geo data
    save_geo_data(output_path, image_path, additional_info, lat, lon, prob, detections)

    # Prepare payload
    payload = {
        "lat": lat,
        "lon": lon,
        "probability": prob,
        "image": os.path.basename(image_path),
        "detections": json.dumps(detections)
    }

    try:
        response = requests.post(endpoint_url, json=payload)
        if response.status_code == 200:
            print(f"Coordinates sent successfully for image: {image_path}")
        else:
            print(f"Server returned status {response.status_code} for image {image_path}: {response.text}")
    except Exception as e:
        print(f"Error sending coordinates for image {image_path}: {e}")

def main():
    if len(sys.argv) < 4:
        print("Usage: python extract_location.py <IMAGE_FOLDER> <ENDPOINT_URL> <OUTPUT_PATH>")
        sys.exit(1)

    image_folder = sys.argv[1]
    endpoint_url = sys.argv[2]
    output_path = sys.argv[3]

    if not os.path.exists(image_folder):
        print(f"Image folder does not exist: {image_folder}")
        sys.exit(1)

    additional_info = "User-provided additional information"

    geoclip_model = GeoCLIP()
    detection_model = load_detection_model()

    for filename in os.listdir(image_folder):
        image_path = os.path.join(image_folder, filename)
        if not os.path.isfile(image_path):
            continue
        if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
            print(f"Skipping non-image file: {filename}")
            continue

        print(f"Processing image: {filename}")
        process_image(image_path, endpoint_url, output_path, geoclip_model, detection_model, additional_info)

if __name__ == "__main__":
    main()

