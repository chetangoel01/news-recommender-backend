# pipeline/summarize.py
from transformers import pipeline
import warnings

# Suppress transformer warnings
warnings.filterwarnings("ignore", category=UserWarning)

summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

def summarize(text, max_length=200, min_length=30):
    # Adaptive max_length based on input length
    input_length = len(text.split())
    
    # If input is very short, return it as-is or use a much smaller max_length
    if input_length < 50:
        return text[:200] + "..." if len(text) > 200 else text
    
    # Adjust max_length to be reasonable compared to input
    adaptive_max_length = min(max_length, max(min_length + 10, input_length // 2))
    adaptive_min_length = min(min_length, adaptive_max_length - 10)
    
    return summarizer(
        text, 
        max_length=adaptive_max_length, 
        min_length=adaptive_min_length, 
        do_sample=False
    )[0]["summary_text"]
