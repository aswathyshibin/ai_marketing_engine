from moviepy import TextClip, ColorClip, CompositeVideoClip
import os

try:
    print("Testing TextClip...")
    txt_clip = TextClip(
        text="Hello World",
        color='white',
        font_size=70,
        font='Arial',
        method='caption',
        size=(640, 480)
    ).with_duration(2)
    
    background = ColorClip(size=(640, 480), color=(0, 0, 0)).with_duration(2)
    video = CompositeVideoClip([background, txt_clip])
    
    output_path = "test_moviepy.mp4"
    video.write_videofile(output_path, fps=24)
    print(f"Success! Video saved to {output_path}")
    if os.path.exists(output_path):
        os.remove(output_path)
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
