# pipeline/summarize.py
from transformers import pipeline

summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

def summarize(text, max_length=200, min_length=30):
    return summarizer(text, max_length=max_length, min_length=min_length, do_sample=False)[0]["summary_text"]
