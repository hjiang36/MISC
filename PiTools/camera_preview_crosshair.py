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
    
    # Convert to PIL image for drawing (ensure it's RGBA for transparency support)
    image = Image.fromarray(frame)
    
    # Create a transparent overlay
    overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    # Draw the red cross overlay with half transparency
    cross_color = (255, 0, 0, 128) # Red with 50% transparency
    center_x, center_y = image.width // 2, image.height // 2
    line_length = 32
    draw.line((center_x - line_length, center_y, center_x + line_length, center_y), fill=cross_color, width=3)
    draw.line((center_x, center_y - line_length, center_x, center_y + line_length), fill=cross_color, width=3)
    
    # Composite the overlay onto the image
    image.paste(overlay, (0, 0), overlay)

    # Convert the image for Tkinter
    tk_image = ImageTk.PhotoImage(image=image.convert("RGB"))  # Convert back to RGB for Tkinter compatibility
    
    # Update the label with the new image
    image_label.config(image=tk_image)
    image_label.image = tk_image
    image_label.after(16, update_image)  # Continue updating the image every 16 ms

# Setup the image label
image_label = tk.Label(root)
image_label.pack()

# Start the update process
update_image()

# Run the Tkinter main loop
root.mainloop()
