import os
import glob

TEMP_DIR = os.path.join(os.path.dirname(__file__), '..', 'assets', 'temp')

def get_temp_path(filename: str) -> str:
    """Returns the full path for a temporary file, ensuring directory exists."""
    os.makedirs(TEMP_DIR, exist_ok=True)
    return os.path.join(TEMP_DIR, filename)

def generate_filename(prefix: str, extension: str, step: int = None) -> str:
    """Generates a consistent filename for intermediate assets."""
    if step is not None:
        return f"{prefix}_{step}.{extension}"
    return f"{prefix}.{extension}"

def clean_temp_files(prefix: str = None):
    """
    Cleans up temp files. If prefix is provided, only deletes files starting with that prefix.
    Used to delete images/audio after video creation.
    """
    if not os.path.exists(TEMP_DIR):
        return
        
    pattern = os.path.join(TEMP_DIR, f"{prefix}*") if prefix else os.path.join(TEMP_DIR, "*")
    
    for filepath in glob.glob(pattern):
        # Prevent deleting the final output .mp4 accidentally
        if filepath.endswith('.mp4') and not prefix:
            continue
            
        try:
            if os.path.isfile(filepath):
                os.remove(filepath)
        except Exception as e:
            print(f"Error deleting file {filepath}: {e}")
