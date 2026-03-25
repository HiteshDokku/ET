import textwrap
from PIL import Image, ImageDraw, ImageFont
from utils.file_manager import get_temp_path, generate_filename

def generate_visual(text: str, step: int) -> str:
    """
    Generates a text slide image using Pillow.
    Returns the path to the generated image file.
    """
    filename = generate_filename("scene_visual", "png", step)
    filepath = get_temp_path(filename)
    
    # Create image 720p
    width, height = 1280, 720
    img = Image.new('RGB', (width, height), color=(15, 23, 42)) # Dark blue-grey background
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("arial.ttf", 60)
    except IOError:
        font = ImageFont.load_default()
        
    wrapped_text = textwrap.fill(text, width=40)
    
    bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (width - text_width) / 2
    y = (height - text_height) / 2
    
    draw.multiline_text((x+3, y+3), wrapped_text, font=font, fill=(51, 65, 85), align="center")
    draw.multiline_text((x, y), wrapped_text, font=font, fill=(248, 250, 252), align="center")
    
    img.save(filepath)
    return filepath
