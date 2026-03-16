from moviepy import TextClip
try:
    from moviepy.config import change_settings
    print("MoviePy config module found.")
except ImportError:
    print("MoviePy config module not found (standard in v1.x).")

try:
    import moviepy
    print(f"MoviePy version: {moviepy.__version__}")
except AttributeError:
    print("Could not determine MoviePy version via __version__")

try:
    print("Available fonts:", TextClip.list('font')[:10], "...")
except Exception as e:
    print(f"Error listing fonts: {e}")
