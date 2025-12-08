from rembg import remove
from PIL import Image
import io

input_path = "/Users/sandeep/VSCODE/LearnBot/gemini-image-2_Cute_2D_Pixar-style_magical_glowing_wisp_wizard_mascot_tiny_floating_upper_body_-0.jpg"
output_path = "/Users/sandeep/VSCODE/LearnBot/wispen_sticker.png"

# Read image
with open(input_path, "rb") as i:
    input_image = i.read()

# Remove background
output_image = remove(input_image)

# Save result
with open(output_path, "wb") as o:
    o.write(output_image)

print("Done! Sticker saved as:", output_path)
