import matplotlib.pyplot as plt
import numpy as np
import matplotlib
matplotlib.use('Agg') # Ensures it doesn't try to open a GUI window
from utils.file_manager import get_temp_path, generate_filename
from services.visual_generator import generate_visual

def extract_numbers_mock(text: str):
    """
    Mock function to create dummy data for the chart based roughly on the length of text.
    """
    return [10, 25, 45, 60, 85, 120]

def generate_chart(text: str, step: int) -> str:
    """
    Generates an animated data chart. If generation fails, falls back to text slide.
    Returns the path to the generated image file.
    """
    try:
        filename = generate_filename("scene_chart", "png", step)
        filepath = get_temp_path(filename)
        
        data = extract_numbers_mock(text)
        
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(1280/100, 720/100), dpi=100)
        
        x = np.arange(len(data))
        ax.plot(x, data, marker='o', color='#3b82f6', linewidth=4, markersize=10)
        ax.fill_between(x, data, color='#3b82f6', alpha=0.3)
        
        ax.set_facecolor('#0f172a')
        fig.patch.set_facecolor('#0f172a')
        
        ax.grid(color='#334155', linestyle='--', alpha=0.5)
        ax.set_title("Data Insights", fontsize=24, color='#f8fafc', pad=20)
        
        plt.tight_layout()
        plt.savefig(filepath, facecolor=fig.get_facecolor(), edgecolor='none')
        plt.close(fig)
        
        return filepath
    except Exception as e:
        print(f"Chart generation failed: {e}. Falling back to text slide.")
        return generate_visual(text, step)
