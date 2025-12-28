# styles.py - Style management
import os
import json
import gradio as gr
from data import STYLES_DIR, DEFAULT_STYLE

def get_style_files():
    """Get list of style JSON files."""
    if not os.path.exists(STYLES_DIR):
        return []
    return [f[:-5] for f in os.listdir(STYLES_DIR) if f.endswith('.json')]

def load_style(name):
    """Load a style from JSON."""
    path = os.path.join(STYLES_DIR, f"{name}.json")
    if os.path.exists(path):
        with open(path, 'r') as f:
            return {**DEFAULT_STYLE, **json.load(f)}
    return None

def save_style(name, positive, negative, loras_text, model_category="Illustrious"):
    """Save a style to JSON."""
    if not name or not name.strip():
        return "❌ Style name cannot be empty!"
    
    name = name.strip()
    loras = [l.strip() for l in loras_text.split('\n') if l.strip()]
    style = {
        "name": name,
        "positive": positive.strip() if positive else "",
        "negative": negative.strip() if negative else "",
        "loras": loras,
        "model_category": model_category
    }
    path = os.path.join(STYLES_DIR, f"{name}.json")
    with open(path, 'w') as f:
        json.dump(style, f, indent=2)
    return f"✅ Style '{name}' saved!"

def delete_style(name):
    """Delete a style."""
    if not name: return "❌ No style selected"
    path = os.path.join(STYLES_DIR, f"{name}.json")
    if os.path.exists(path):
        os.remove(path)
        return f"🗑️ Style '{name}' deleted!"
    return "❌ Style not found"

def load_style_ui(name):
    """Load style data for UI."""
    if not name:
        return "", "", "", "Illustrious"
    style = load_style(name)
    if not style:
        return "", "", "", "Illustrious"
    return style.get("positive", ""), style.get("negative", ""), "\n".join(style.get("loras", [])), style.get("model_category", "Illustrious")
