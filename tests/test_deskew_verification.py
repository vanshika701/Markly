import os

import cv2

from utils.image_utils import deskew, detect_skew_angle

output_dir = "output/deskew_verification"
os.makedirs(output_dir, exist_ok=True)

# A clean, full-frame page (no background clutter) — load straight to grayscale
image = cv2.imread("output/converted_pages/page_1.png", cv2.IMREAD_GRAYSCALE)
cv2.imwrite(os.path.join(output_dir, "1_original.png"), image)

# Deliberately rotate it by a known angle to simulate a tilted scan
known_angle = -5
height, width = image.shape[:2]
center = (width // 2, height // 2)
matrix = cv2.getRotationMatrix2D(center, known_angle, 1.0)
tilted = cv2.warpAffine(
    image, matrix, (width, height), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
)
cv2.imwrite(os.path.join(output_dir, "2_tilted.png"), tilted)

before = detect_skew_angle(tilted)
print(f"Tilted by {known_angle} degrees -> detect_skew_angle reports: {before:.2f} degrees")

corrected = deskew(tilted)
cv2.imwrite(os.path.join(output_dir, "3_corrected.png"), corrected)

after = detect_skew_angle(corrected)
print(f"After deskew() -> detect_skew_angle reports: {after:.2f} degrees (target: ~0)")

tolerance = 1.0
if abs(after) < tolerance:
    print(f"PASS: residual angle is within {tolerance} degrees of level")
else:
    print(f"FAIL: residual angle {after:.2f} exceeds tolerance of {tolerance} degrees")
