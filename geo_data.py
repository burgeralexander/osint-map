#!/usr/bin/env python3

import torch
from geoclip import GeoCLIP
import requests
import sys
import os
from PIL import Image
import piexif

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

def save_geo_data(output_path, image_path, additional_info, lat, lon, prob):
    """Save extracted geo data to a text file."""
    try:
        with open(output_path, "a") as file:
            file.write(f"Image: {image_path}\n")
            file.write(f"Additional Info: {additional_info}\n")
            file.write(f"Latitude: {lat:.6f}\n")
            file.write(f"Longitude: {lon:.6f}\n")
            file.write(f"Probability: {prob:.6f}\n")
            file.write("\n")
    except Exception as e:
        print(f"Error saving geo data: {e}")

def process_image(image_path, endpoint_url, output_path, model, additional_info):
    """Process a single image for geolocation extraction."""
    # Check for metadata geolocation
    metadata_coords = extract_metadata_geolocation(image_path)

    if metadata_coords:
        lat, lon = metadata_coords
        print(f"Metadata Geolocation Found: Latitude={lat:.6f}, Longitude={lon:.6f}")
        prob = 1.0  # Assume confidence is 100% for metadata geolocation
    else:
        print("No metadata geolocation found. Running GeoCLIP.")

        # Predict top GPS coordinates
        top_pred_gps, top_pred_prob = model.predict(image_path, top_k=1)  # Get top 1 prediction

        if top_pred_gps is None or len(top_pred_gps) == 0:
            print(f"No GPS coordinates found for the image: {image_path}")
            return

        # Extract the top prediction
        lat_tensor, lon_tensor = top_pred_gps[0]
        prob_tensor = top_pred_prob[0]

        # Convert Tensors to Python floats
        lat = lat_tensor.item()
        lon = lon_tensor.item()
        prob = prob_tensor.item()

    print(f"Extracted Coordinates: Latitude={lat:.6f}, Longitude={lon:.6f}, Probability={prob:.6f}")

    # Save geo data to the text file
    save_geo_data(output_path, image_path, additional_info, lat, lon, prob)

    # Prepare payload
    payload = {
        "lat": lat,
        "lon": lon,
        "probability": prob,
        "image": os.path.basename(image_path)  # Optional: Send image name
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

    # Initialize GeoCLIP model
    model = GeoCLIP()

    # Process each image in the folder
    for filename in os.listdir(image_folder):
        image_path = os.path.join(image_folder, filename)
        if not os.path.isfile(image_path):
            continue
        if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
            print(f"Skipping non-image file: {filename}")
            continue

        print(f"Processing image: {filename}")
        process_image(image_path, endpoint_url, output_path, model, additional_info)

if __name__ == "__main__":
    main()

