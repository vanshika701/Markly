import os

from utils.pdf_utils import convert_pdf_to_images

pdf_path = "samples/handwritten.pdf"
output_dir = "output/converted_pages"

os.makedirs(output_dir, exist_ok=True)

images = convert_pdf_to_images(pdf_path)
print(f"{pdf_path}: converted into {len(images)} page image(s)")

for i, image in enumerate(images, start=1):
    width, height = image.size
    out_path = os.path.join(output_dir, f"page_{i}.png")
    image.save(out_path)
    print(f"  Page {i}: {width}x{height} px, mode={image.mode} -> saved to {out_path}")
