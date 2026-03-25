from utils.text_cleaner import clean_article_text
from utils.file_manager import clean_temp_files
from services.summarizer import generate_summary
from services.script_generator import generate_script
from services.scene_generator import generate_scenes
from services.voice_generator import generate_voice
from services.visual_generator import generate_visual
from services.chart_generator import generate_chart
from services.video_assembler import assemble_video

def generate_video_pipeline(article: str) -> str:
    """
    Orchestrates the complete video generation flow.
    Returns the filename of the generated video.
    """
    try:
        # Step 1: Clean Text
        print("Cleaning text...")
        clean_text = clean_article_text(article)
        
        # Step 2: Generate Summary
        print("Generating summary...")
        summary = generate_summary(clean_text)
        
        # Step 3: Generate Script
        print("Generating script...")
        script = generate_script(summary)
        
        # Step 4: Generate Scenes
        print("Generating scenes...")
        scenes = generate_scenes(script)
        
        # Step 5: Process Scenes
        print(f"Processing {len(scenes)} scenes...")
        scene_assets = []
        for i, scene in enumerate(scenes):
            step = i + 1
            text = scene.get("text", "")
            scene_type = scene.get("type", "text")
            
            # Voice Generation
            audio_path = generate_voice(text, step)
            
            # Visual Generation
            if scene_type == "data":
                img_path = generate_chart(text, step)
            else:
                img_path = generate_visual(text, step)
                
            scene_assets.append({
                "image": img_path,
                "audio": audio_path
            })
            
        # Step 6: Assemble Video
        print("Assembling video...")
        output_filename = assemble_video(scene_assets)
        
        # Step 7: Cleanup
        print("Cleaning up temp assets...")
        clean_temp_files(prefix="scene_")
        
        print(f"Video created successfully: {output_filename}")
        return output_filename
        
    except Exception as e:
        print(f"Pipeline error: {e}")
        # Clean up in case of failure
        clean_temp_files()
        raise e
