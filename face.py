import os
from facedb import FaceDB
from PIL import Image

# Function to preprocess images
def preprocess_image(img_path):
    try:
        with Image.open(img_path) as img:
            img = img.convert("RGB")  # Ensure the image is in RGB format
            img = img.resize((300, 300))  # Resize to a smaller standard size (adjust as needed)
            img.save(img_path)  # Overwrite the original file or save as a new file
    except Exception as e:
        print(f"Error preprocessing image {img_path}: {e}")

# Create a FaceDB instance
db = FaceDB(
    path="facedata",
)

# Define the folder containing images to be added to the database
folder_path = "/home/a/Schreibtisch/Project/Project_A/projects/Project_B_0.1/downloads/"

# Add all images in the folder to the database
for filename in os.listdir(folder_path):
    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
        name = os.path.splitext(filename)[0]  # Use the filename (without extension) as the face name
        img_path = os.path.join(folder_path, filename)

        # Preprocess the image
        preprocess_image(img_path)

        try:
            face_id = db.add(name, img=img_path)
            print(f"Added {name} to the database with ID: {face_id}")
        except ValueError as e:
            print(f"Error adding {filename}: {e}")
        except Exception as e:
            print(f"Unexpected error with {filename}: {e}")

# Recognize faces for a new set of images
recognition_folder = "new_faces_folder"
for filename in os.listdir(recognition_folder):
    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
        img_path = os.path.join(recognition_folder, filename)

        # Preprocess the image
        preprocess_image(img_path)

        try:
            result = db.recognize(img=img_path)
            if result:
                print(f"Image {filename} recognized as {result['name']} with ID: {result['id']}")
            else:
                print(f"Image {filename} is unknown")
        except Exception as e:
            print(f"Error recognizing {filename}: {e}")

