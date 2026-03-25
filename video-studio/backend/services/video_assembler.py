from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
from utils.file_manager import get_temp_path, generate_filename
import os
import uuid

def assemble_video(scene_assets: list[dict]) -> str:
    """
    Assembles images and audio clips sequentially into a final MP4 video.
    scene_assets: [{'image': path, 'audio': path}, ...]
    Returns the filename of the final video.
    """
    clips = []
    
    for asset in scene_assets:
        img_path = asset.get("image")
        audio_path = asset.get("audio")
        
        if not os.path.exists(img_path) or not os.path.exists(audio_path):
            print(f"Skipping scene due to missing assets: {img_path}, {audio_path}")
            continue
            
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
        
        # MoviePy 2.x uses with_duration and with_audio instead of set_duration and set_audio
        img_clip = ImageClip(img_path).with_duration(duration)
        video_clip = img_clip.with_audio(audio_clip)
        
        clips.append(video_clip)
        
    if not clips:
        raise ValueError("No valid scenes to assemble.")
        
    final_video = concatenate_videoclips(clips, method="compose")
    
    filename = f"output_{uuid.uuid4().hex[:8]}.mp4"
    filepath = get_temp_path(filename)
    
    final_video.write_videofile(
        filepath, 
        fps=24, 
        codec="libx264", 
        audio_codec="aac",
        logger=None # Suppress verbose output
    )
    
    # Close clips to free resources
    for clip in clips:
        clip.close()
    final_video.close()
        
    return filename
