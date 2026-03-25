from gtts import gTTS
from utils.file_manager import get_temp_path, generate_filename

def generate_voice(text: str, step: int) -> str:
    """
    Generates a voice MP3 file using gTTS for the given text.
    Returns the path to the generated audio file.
    """
    filename = generate_filename("scene_audio", "mp3", step)
    filepath = get_temp_path(filename)
    
    tts = gTTS(text=text, lang='en', slow=False)
    tts.save(filepath)
    
    return filepath
