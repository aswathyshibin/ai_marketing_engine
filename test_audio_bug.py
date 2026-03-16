import asyncio
import os
import edge_tts
from moviepy import AudioFileClip, ColorClip

async def test_audio_duration_bug():
    text = "Join now." # Very short burst
    output_path = "output/temp/test_short_audio.mp3"
    
    print("1. Generating short TTS...")
    communicate = edge_tts.Communicate(text, "en-US-GuyNeural")
    await communicate.save(output_path)
    
    print("2. Reading with MoviePy...")
    try:
        audio = AudioFileClip(output_path)
        duration = audio.duration
        print(f"Success! Detected Duration: {duration} seconds")
        
        print("3. Attaching to Video Clip...")
        # Create a dummy video of exactly that duration
        bg = ColorClip(size=(640, 480), color=(15, 23, 42)).with_duration(duration)
        video = bg.with_audio(audio)
        
        print("4. Writing video file...")
        video.write_videofile("output/reels/test_audio_bug.mp4", fps=24, codec="libx264", audio_codec="aac")
        print("Success! No avcodec error.")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_audio_duration_bug())
