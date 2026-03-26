import os
import sys

# Add project root to sys.path
sys.path.append(os.getcwd())

def test_font_paths():
    font_paths = [
        os.path.join("assets", "fonts", "Inter-Bold.ttf"), # Bundled
        "/usr/share/fonts/opentype/inter/Inter-Bold.otf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf" # Windows fallback
    ]
    
    found = False
    for path in font_paths:
        exists = os.path.exists(path)
        print(f"Checking {path}... {'EXISTS' if exists else 'NOT FOUND'}")
        if exists:
            print(f"SUCCESS: Using font at {path}")
            found = True
            break
            
    if not found:
        print("WARNING: No specialized fonts found. Falling back to default.")

if __name__ == "__main__":
    test_font_paths()
