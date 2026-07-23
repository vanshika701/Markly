import os

import cv2

from utils.image_utils import to_grayscale, denoise, enhance_contrast, deskew

samples = ["messy_scan.jpg", "messy_scan1.jpg"]
output_root = "output/preprocessed"

for filename in samples:
    name = os.path.splitext(filename)[0]
    out_dir = os.path.join(output_root, name)
    os.makedirs(out_dir, exist_ok=True)

    image = cv2.imread(os.path.join("samples", filename))
    print(f"{filename}: original shape={image.shape}")

    gray = to_grayscale(image)
    cv2.imwrite(os.path.join(out_dir, "1_gray.png"), gray)

    denoised = denoise(gray)
    cv2.imwrite(os.path.join(out_dir, "2_denoised.png"), denoised)

    contrast = enhance_contrast(denoised)
    cv2.imwrite(os.path.join(out_dir, "3_contrast.png"), contrast)

    deskewed = deskew(contrast)
    cv2.imwrite(os.path.join(out_dir, "4_deskewed.png"), deskewed)

    print(f"  saved 1_gray.png, 2_denoised.png, 3_contrast.png, 4_deskewed.png -> {out_dir}/")
