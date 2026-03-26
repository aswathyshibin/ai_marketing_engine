import os
from PIL import ImageFont

def find_malayalam_fonts():
    # Common Windows font directory
    font_dir = r"C:\Windows\Fonts"
    test_char = "\u0d05" # Malayalam letter A
    
    malayalam_fonts = []
    
    if os.path.exists(font_dir):
        for font_file in os.listdir(font_dir):
            if font_file.lower().endswith(('.ttf', '.otf')):
                font_path = os.path.join(font_dir, font_file)
                try:
                    font = ImageFont.truetype(font_path, 12)
                    mask = font.getmask(test_char)
                    if mask.getbbox() is not None:
                        malayalam_fonts.append(font_path)
                except:
                    continue
                    
    return malayalam_fonts

if __name__ == "__main__":
    fonts = find_malayalam_fonts()
    print("MATCHING_FONTS_START")
    for f in fonts:
        print(f)
    print("MATCHING_FONTS_END")
