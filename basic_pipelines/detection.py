import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import os
import numpy as np
import cv2
import hailo
import serial
import time
import socket

from hailo_apps_infra.hailo_rpi_common import (
    get_caps_from_pad,
    get_numpy_from_buffer,
    app_callback_class,
)
from hailo_apps_infra.detection_pipeline import GStreamerDetectionApp

# -----------------------------------------------------------------------------------------------
# User-defined class to be used in the callback function
# -----------------------------------------------------------------------------------------------
# Inheritance from the app_callback_class
class user_app_callback_class(app_callback_class):

    def __init__(self):
        super().__init__()

    #def new_function(self):  # New function example
        # ser = serial.Serial('/dev/ttyAMA10', 115200, timeout=1)  # New variable example
        # # Write data to STM32
        # ser.write(b'ping from RPi\n')
    
        # # Read 10 bytes from STM32
        # rx_buffer = ser.read(10)
        # if rx_buffer:
        #     print(f"Received: {rx_buffer.decode('utf-8', errors='ignore')}")

# -----------------------------------------------------------------------------------------------
# User-defined callback function
# -----------------------------------------------------------------------------------------------

# UDP socket setup (bunu bir defa yap, callback içinde değil!)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_address = ('localhost', 5005)  # localhost ve port

# Add a global variable to store the last detection details
last_detection = {"label": None, "confidence": None, "bbox": None}

# This is the callback function that will be called when data is available from the pipeline
def app_callback(pad, info, user_data):
    global last_detection  # Access the global variable
    # Get the GstBuffer from the probe info
    buffer = info.get_buffer()
    # Check if the buffer is valid
    if buffer is None:
        return Gst.PadProbeReturn.OK

    # Using the user_data to count the number of frames
    user_data.increment()
    string_to_print = f"Frame count: {user_data.get_count()}\n"

    # Get the caps from the pad
    format, width, height = get_caps_from_pad(pad)

    # If the user_data.use_frame is set to True, we can get the video frame from the buffer
    frame = None
    if user_data.use_frame and format is not None and width is not None and height is not None:
        # Get video frame
        frame = get_numpy_from_buffer(buffer, format, width, height)

    # Get the detections from the buffer
    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)

    # Parse the detections
    detection_count = 0
    for detection in detections:
        label = detection.get_label()
        bbox = detection.get_bbox()
        confidence = detection.get_confidence()
    
        # Call the methods to get the actual bounding box values
        x_min, y_min, x_max, y_max = bbox.xmin(), bbox.ymin(), bbox.xmax(), bbox.ymax()
    
        # Format the message with usable bbox coordinates
        message = f"{label},{confidence:.2f},{x_min},{y_min},{x_max},{y_max}"
        sock.sendto(message.encode(), server_address)
    
        last_detection = {"label": label, "confidence": confidence, "bbox": (x_min, y_min, x_max, y_max)}  # Update last detection
        if label == "a":
            # Get track ID
            track_id = 0
            track = detection.get_objects_typed(hailo.HAILO_UNIQUE_ID)
            if len(track) == 1:
                track_id = track[0].get_id()
            
            string_to_print += (f"Detection: ID: {track_id} Label: {label} Confidence: {confidence:.2f}\n")
            detection_count += 1

    # If no detections, send the last detection details
    if detection_count == 0 and last_detection["label"] is not None:
        message = f"{last_detection['label']},{last_detection['confidence']:.2f},{last_detection['bbox']}"
        sock.sendto(message.encode(), server_address)

    if user_data.use_frame:
        # Note: using imshow will not work here, as the callback function is not running in the main thread
        # Let's print the detection count to the frame
        cv2.putText(frame, f"Detections: {detection_count}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        # Example of how to use the new_variable and new_function from the user_data
        # Let's print the new_variable and the result of the new_function to the frame
        cv2.putText(frame, f"{user_data.new_function()} {user_data.new_variable}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        # Convert the frame to BGR
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        user_data.set_frame(frame)

    print(string_to_print)
    return Gst.PadProbeReturn.OK

if __name__ == "__main__":
    # Create an instance of the user app callback class
    user_data = user_app_callback_class()
    app = GStreamerDetectionApp(app_callback, user_data)
    app.run()
