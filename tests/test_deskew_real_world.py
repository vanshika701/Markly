import os

import cv2

from utils.image_utils import deskew, detect_skew_angle

samples = ["messy_scan", "messy_scan1"]
known_angle = 5
tolerance = 1.0

for name in samples:
    output_dir = os.path.join("output", "deskew_verification_real", name)
    os.makedirs(output_dir, exist_ok=True)

    base = cv2.imread(os.path.join("output", "preprocessed", name, "3_contrast.png"), cv2.IMREAD_GRAYSCALE)

    baseline = detect_skew_angle(base)
    print(f"{name}: baseline detected angle = {baseline:.2f} degrees")

    height, width = base.shape[:2]
    center = (width // 2, height // 2)
    matrix = cv2.getRotationMatrix2D(center, known_angle, 1.0)
    tilted = cv2.warpAffine(base, matrix, (width, height), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    cv2.imwrite(os.path.join(output_dir, "1_tilted.png"), tilted)

    before = detect_skew_angle(tilted)
    print(f"  after adding {known_angle} degrees -> {before:.2f} (expected ~{baseline + known_angle:.2f})")

    corrected = deskew(tilted)
    cv2.imwrite(os.path.join(output_dir, "2_corrected.png"), corrected)

    after = detect_skew_angle(corrected)
    print(f"  after deskew() -> {after:.2f} (target: back to baseline ~{baseline:.2f})")

    residual = abs(after - baseline)
    if residual < tolerance:
        print(f"  PASS: added tilt removed, within {tolerance} degrees of baseline")
    else:
        print(f"  FAIL: residual difference {residual:.2f} exceeds tolerance {tolerance}")
    print()
