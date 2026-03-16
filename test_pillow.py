from moviepy import ImageClip, CompositeVideoClip, ColorClip
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os

def create_text_image(text, width=1080, height=None, font_path=None, font_size=80, color="white"):
    """Creates a numpy array of an image containing the text using Pillow."""
    # Create a temporary image to calculate text size
    dummy_img = Image.new('RGBA', (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    
    try:
        font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()
    except Exception as e:
        print(f"Error loading font {font_path}: {e}")
        font = ImageFont.load_default()
        
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    
    # Add some padding
    img_w = width if width else text_w + 40
    img_h = height if height else text_h + 40
    
    img = Image.new('RGBA', (img_w, img_h), (0, 0, 0, 0)) # Transparent background
    draw = ImageDraw.Draw(img)
    
    # Center text
    x = (img_w - text_w) / 2
    y = (img_h - text_h) / 2
    
    draw.text((x, y), text, font=font, fill=color)
    
    return np.array(img)

try:
    print("Testing Pillow text generation...")
    text_arr = create_text_image(
        "HELLO WORLD\nWITH PILLOW", 
        width=800, 
        font_path="C:\\Windows\\Fonts\\arialbd.ttf", 
        font_size=100
    )
    
    txt_clip = ImageClip(text_arr).with_duration(2)
    background = ColorClip(size=(800, 400), color=(50, 50, 50)).with_duration(2)
    
    # Center the text clip on the background
    txt_clip = txt_clip.with_position('center')
    
    video = CompositeVideoClip([background, txt_clip])
    
    output_path = "test_pillow_moviepy.mp4"
    video.write_videofile(output_path, fps=24, logger=None)
    print(f"Success! Video saved to {output_path}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
