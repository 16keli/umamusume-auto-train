import platform

if platform.system() == "Windows":
    import dxcam_cpp as dxcam
else:
    import dxcam

from time import sleep

import cv2
import pygetwindow
from PIL import Image

win = pygetwindow.getWindowsWithTitle("Umamusume")
target_window: pygetwindow.BaseWindow = next((w for w in win if w.title.strip() == "Umamusume"), None)


def box_to_bounds(box: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    left, top, width, height = box
    right = left + width
    bottom = top + height
    return (left, top, right, bottom)


print(target_window.box)

target_window.activate()

cam = dxcam.create()

sleep(0.5)

img = cam.grab(region=box_to_bounds(target_window.box))

gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# Apply Gaussian Blur to reduce noise
# blur = cv2.GaussianBlur(gray_img, (5, 5), 1.4)

sobelx = cv2.Sobel(gray_img, cv2.CV_64F, 1, 0, ksize=3)  # dx=1, dy=0 for vertical edges

# Convert to uint8
gradient_magnitude = cv2.convertScaleAbs(sobelx)

Image.fromarray(gradient_magnitude).show()

# Apply thresholding to create a binary image
_, thresh = cv2.threshold(gradient_magnitude, 127, 255, cv2.THRESH_BINARY)

# Find contours
contours, hierarchy = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

# Draw contours (optional)
cv2.drawContours(img, contours, -1, (0, 255, 0), 2)  # Draw all contours in green with thickness 2

Image.fromarray(img).show()
