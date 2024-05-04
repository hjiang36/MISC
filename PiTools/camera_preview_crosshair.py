"""
This script shows a live preview from the camera with a red cross overlay in the center.

This script depends on tk, which can be installed by running the following command on the Raspberry Pi:
    sudo apt-get install python3-pil.imagetk

"""

import tkinter as tk
from PIL import Image, ImageTk, ImageDraw
from picamera2 import Picamera2, Preview
import numpy as np

# Create the main window
root = tk.Tk()
root.title("Camera Preview with Overlay")

# Initialize Picamera2
picam2 = Picamera2()
picam2.start_preview(Preview.QTGL)
config = picam2.create_preview_configuration(main={"size": (640, 480)})
picam2.configure(config)
picam2.start()

# Function to update the image on the label
def update_image():
    # Get an image from the camera
    frame = picam2.capture_array()
    
    # Convert to PIL image for drawing
    image = Image.fromarray(frame)
    draw = ImageDraw.Draw(image)

    # Draw the red cross overlay
    cross_color = (255, 0, 0)  # Red
    center_x, center_y = image.width // 2, image.height // 2
    line_length = 50
    draw.line((center_x - line_length, center_y, center_x + line_length, center_y), fill=cross_color, width=5)
    draw.line((center_x, center_y - line_length, center_x, center_y + line_length), fill=cross_color, width=5)
    
    # Convert the image for Tkinter
    tk_image = ImageTk.PhotoImage(image=image)
    
    # Update the label with the new image
    image_label.config(image=tk_image)
    image_label.image = tk_image
    image_label.after(10, update_image)  # Continue updating the image every 10 ms

# Setup the image label
image_label = tk.Label(root)
image_label.pack()

# Start the update process
update_image()

# Run the Tkinter main loop
root.mainloop()
