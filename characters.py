# characters.py - Character management and presets
import os
import json
import gradio as gr

from data import CHARACTERS_DIR, PRESETS_DIR, GEN_CONFIG_FILE, DEFAULT_CHARACTER, DEFAULT_GEN_CONFIG
from config import (
    load_gen_config, get_all_outfit_keys, get_all_morph_keys, get_all_body_keys,
    get_height_guide_label
)

def get_character_files():
    """Get list of character JSON files."""
    if not os.path.exists(CHARACTERS_DIR):
        return []
    return [f[:-5] for f in os.listdir(CHARACTERS_DIR) if f.endswith('.json')]

def load_character(name):
    """Load a character from JSON."""
    path = os.path.join(CHARACTERS_DIR, f"{name}.json")
    if os.path.exists(path):
        with open(path, 'r') as f:
            return {**DEFAULT_CHARACTER, **json.load(f)}
    return None

def save_character(name, positive, negative, outfits, morphs, active, body=None, loras=None, height_guide="average", model_category="Illustrious"):
    """Save a character to JSON."""
    char = {
        "name": name,
        "positive": positive,
        "negative": negative,
        "outfits": outfits,
        "morphs": morphs,
        "body": body if body is not None else {},
        "loras": loras if loras is not None else [],
        "active": active,
        "height_guide": height_guide,
        "model_category": model_category
    }
    path = os.path.join(CHARACTERS_DIR, f"{name}.json")
    with open(path, 'w') as f:
        json.dump(char, f, indent=2)
    return f"✅ Character '{name}' saved!"

def save_character_from_ui(name, positive, negative, loras_text, height_guide, model_category, *all_values):
    """Save character from UI with outfit, morph, body textboxes, and height guide."""
    outfit_keys = get_all_outfit_keys()
    morph_keys = get_all_morph_keys()
    body_keys = get_all_body_keys()
    
    outfits = {}
    morphs = {}
    body = {}
    
    ptr = 0
    for key in outfit_keys:
        pos = all_values[ptr] if ptr < len(all_values) else ""
        neg = all_values[ptr+1] if ptr+1 < len(all_values) else ""
        outfits[key] = {"positive": pos or "", "negative": neg or ""}
        ptr += 2
        
    for key in morph_keys:
        pos = all_values[ptr] if ptr < len(all_values) else ""
        neg = all_values[ptr+1] if ptr+1 < len(all_values) else ""
        morphs[key] = {"positive": pos or "", "negative": neg or ""}
        ptr += 2

    for key in body_keys:
        pos = all_values[ptr] if ptr < len(all_values) else ""
        neg = all_values[ptr+1] if ptr+1 < len(all_values) else ""
        body[key] = {"positive": pos or "", "negative": neg or ""}
        ptr += 2
    
    loras = [l.strip() for l in loras_text.split('\n') if l.strip()]
    
    char = load_character(name)
    active = char.get("active", True) if char else True
    
    # Normalize height_guide to key if label was passed
    from data import HEIGHT_GUIDES
    if height_guide not in HEIGHT_GUIDES:
        # Try to find key from label
        for k, v in HEIGHT_GUIDES.items():
            if v["label"] == height_guide:
                height_guide = k
                break
        else:
            height_guide = "average"
    
    return save_character(name, positive, negative, outfits, morphs, active, body, loras, height_guide, model_category)

def delete_character(name):
    """Delete a character."""
    if not name: return "❌ No character selected"
    path = os.path.join(CHARACTERS_DIR, f"{name}.json")
    if os.path.exists(path):
        os.remove(path)
        return f"🗑️ Character '{name}' deleted!"
    return "❌ Character not found"

def rename_character(old_name, new_name):
    """Rename a character JSON file."""
    if not old_name or not new_name:
        return "❌ Names cannot be empty"
    
    old_path = os.path.join(CHARACTERS_DIR, f"{old_name}.json")
    new_path = os.path.join(CHARACTERS_DIR, f"{new_name}.json")
    
    if os.path.exists(new_path):
        return f"❌ Error: Character '{new_name}' already exists"
    
    if os.path.exists(old_path):
        char = load_character(old_name)
        char["name"] = new_name
        with open(new_path, 'w') as f:
            json.dump(char, f, indent=2)
        os.remove(old_path)
        return f"✅ Character '{old_name}' renamed to '{new_name}'"
    return "❌ Original character not found"

def get_active_characters():
    """Get list of active characters."""
    active = []
    for name in get_character_files():
        char = load_character(name)
        if char and char.get("active", False):
            active.append(char)
    return active

def get_preset_files():
    """Get list of preset files."""
    presets = []
    if os.path.exists(PRESETS_DIR):
        presets = [f[:-5] for f in os.listdir(PRESETS_DIR) if f.endswith('.json')]
    return presets


def save_preset(preset_name, active_names=None):
    """Save current active characters as a preset."""
    if not preset_name or not preset_name.strip():
        return "❌ Preset name cannot be empty!"
    
    preset_name = preset_name.strip()
    if active_names is None:
        # Fallback to reading files if no list provided (legacy)
        active_names = [c["name"] for c in get_active_characters()]
        
    path = os.path.join(PRESETS_DIR, f"{preset_name}.json")
    with open(path, 'w') as f:
        json.dump({"active": active_names}, f, indent=2)
    return f"✅ Preset '{preset_name}' saved with {len(active_names)} characters!"

def delete_preset(preset_name):
    """Delete a character preset."""
    if not preset_name:
        return "❌ No preset name provided."
    if preset_name == "All Characters":
        return "❌ Cannot delete 'All Characters'."
        
    path = os.path.join(PRESETS_DIR, f"{preset_name}.json")
    if os.path.exists(path):
        os.remove(path)
        return f"🗑️ Preset '{preset_name}' deleted."
    else:
        return f"❌ Preset '{preset_name}' not found."

def get_generated_presets():
    """Get list of generated presets based on model categories.
    
    These are virtual presets that aren't stored as files.
    Only category-specific presets (e.g. 'All Illustrious Characters') are returned.
    """
    from data import MODEL_CATEGORIES
    
    # Check which categories have at least one character
    categories_with_chars = set()
    all_chars = get_character_files()
    for name in all_chars:
        char = load_character(name)
        if char:
            cat = char.get("model_category", "Illustrious")
            categories_with_chars.add(cat)
            
    presets = []
    # Add presets for existing categories in order
    for cat in MODEL_CATEGORIES:
        if cat in categories_with_chars:
            presets.append(f"All {cat} Characters")
    
    # Note: "All Characters" removed - use category-specific presets instead
    return presets

def load_preset(preset_name):
    """Load a preset and activate those characters."""
    all_chars = get_character_files()
    
    # Handle Dynamic "All {Category} Characters"
    if preset_name.startswith("All ") and preset_name.endswith(" Characters"):
        target_category = preset_name[4:-11] # Extract "Illustrious" from "All Illustrious Characters"
        
        # Handle the generic "All Characters" case (target_category would be empty string technically if we sliced strictly, 
        # but let's handle "All Characters" explicitly or via the slice check)
        
        if preset_name == "All Characters":
             for name in all_chars:
                char = load_character(name)
                if char:
                    char["active"] = True
                    char_path = os.path.join(CHARACTERS_DIR, f"{name}.json")
                    with open(char_path, 'w') as f:
                        json.dump(char, f, indent=2)
             return f"✅ All {len(all_chars)} characters activated", all_chars

        # Handle specific categories
        count = 0
        active_list = []
        for name in all_chars:
            char = load_character(name)
            if char:
                # If specific category, check it. 
                # Note: "All Characters" logic above already caught the generic case.
                should_be_active = (char.get("model_category", "Illustrious") == target_category)
                
                char["active"] = should_be_active
                if should_be_active:
                    count += 1
                    active_list.append(name)
                    
                char_path = os.path.join(CHARACTERS_DIR, f"{name}.json")
                with open(char_path, 'w') as f:
                    json.dump(char, f, indent=2)
                    
        return f"✅ Activated {count} {target_category} characters", active_list
    
    path = os.path.join(PRESETS_DIR, f"{preset_name}.json")
    if not os.path.exists(path):
        return "❌ Preset not found", []
    
    with open(path, 'r') as f:
        preset = json.load(f)
    
    active_names = preset.get("active", [])
    if active_names is None:
        active_names = []
    
    for name in all_chars:
        char = load_character(name)
        if char:
            char["active"] = name in active_names
            char_path = os.path.join(CHARACTERS_DIR, f"{name}.json")
            with open(char_path, 'w') as f:
                json.dump(char, f, indent=2)
    
    return f"✅ Loaded preset '{preset_name}' - {len(active_names)} characters active", active_names

def activate_all_characters():
    """Activate all characters."""
    all_chars = get_character_files()
    for name in all_chars:
        char = load_character(name)
        if char:
            char["active"] = True
            char_path = os.path.join(CHARACTERS_DIR, f"{name}.json")
            with open(char_path, 'w') as f:
                json.dump(char, f, indent=2)
    return f"✅ All {len(all_chars)} characters activated"

def deactivate_all_characters():
    """Deactivate all characters."""
    all_chars = get_character_files()
    for name in all_chars:
        char = load_character(name)
        if char:
            char["active"] = False
            char_path = os.path.join(CHARACTERS_DIR, f"{name}.json")
            with open(char_path, 'w') as f:
                json.dump(char, f, indent=2)
    return f"❌ All {len(all_chars)} characters deactivated"


def refresh_character_list():
    """Refresh the character dropdown."""
    chars = get_character_files()
    return gr.update(choices=chars, value=chars[0] if chars else None)

def load_character_ui(name):
    """Load character data for UI - returns values for all inputs including height_guide."""
    gen_cfg = load_gen_config()
    outfit_keys = list(gen_cfg.get("outfit_names", DEFAULT_GEN_CONFIG["outfit_names"]).keys())
    morph_keys = list(gen_cfg.get("morph_names", DEFAULT_GEN_CONFIG["morph_names"]).keys())
    body_keys = list(gen_cfg.get("body_names", DEFAULT_GEN_CONFIG["body_names"]).keys())
    
    # Default empty result: [positive, negative, loras, height_guide_label, model_category, ...outfit/morph/body pairs]
    empty_res = ["", "", "", "Average", "Illustrious"] + [""] * (len(outfit_keys) * 2 + len(morph_keys) * 2 + len(body_keys) * 2)
    
    if not name:
        return empty_res
    
    char = load_character(name)
    if not char:
        return empty_res
    
    result = [char.get("positive", ""), char.get("negative", "")]
    loras = char.get("loras", [])
    result.append("\n".join(loras))
    
    # Get height guide label for display
    height_guide_key = char.get("height_guide", "average")
    height_guide_label = get_height_guide_label(height_guide_key)
    result.append(height_guide_label)
    result.append(char.get("model_category", "Illustrious"))
    
    def get_pn(data, key):
        val = data.get(key, {})
        if isinstance(val, str): return [val, ""]
        return [val.get("positive", ""), val.get("negative", "")]

    outfits = char.get("outfits", {})
    for key in outfit_keys:
        result.extend(get_pn(outfits, key))
        
    morphs = char.get("morphs", {})
    for key in morph_keys:
        result.extend(get_pn(morphs, key))

    body = char.get("body", {})
    for key in body_keys:
        result.extend(get_pn(body, key))
    
    return result

def get_body_presets():
    """Get list of body presets."""
    gen_cfg = load_gen_config()
    presets = gen_cfg.get("body_presets", {})
    return sorted(list(presets.keys()))

def save_body_preset(name, selection):
    """Save current body part selection as a preset."""
    if not name or not selection:
        return "❌ Name and selection required", gr.update()
    gen_cfg = load_gen_config()
    presets = gen_cfg.get("body_presets", {})
    presets[name] = selection
    gen_cfg["body_presets"] = presets
    with open(GEN_CONFIG_FILE, 'w') as f:
        json.dump(gen_cfg, f, indent=2)
    return f"✅ Preset '{name}' saved!", gr.update(choices=get_body_presets(), value=name)

def load_body_preset(name):
    """Load a body preset - returns selection for dropdown."""
    if not name:
        return []
    gen_cfg = load_gen_config()
    presets = gen_cfg.get("body_presets", {})
    return presets.get(name, [])

def delete_body_preset(name):
    """Delete a body preset."""
    if not name:
        return "❌ No preset selected", gr.update()
    gen_cfg = load_gen_config()
    presets = gen_cfg.get("body_presets", {})
    if name in presets:
        del presets[name]
        gen_cfg["body_presets"] = presets
        with open(GEN_CONFIG_FILE, 'w') as f:
            json.dump(gen_cfg, f, indent=2)
        return f"🗑️ Preset '{name}' deleted!", gr.update(choices=get_body_presets(), value=None)
    return "❌ Preset not found", gr.update()

def create_new_character(name, model_category="Illustrious"):
    """Create a new character."""
    if not name or not name.strip():
        return "❌ Please enter a name", gr.update()
    name = name.strip()
    save_character(name, "", "", {}, {}, True, model_category=model_category)
    return f"✅ Character '{name}' created!", gr.update(choices=get_character_files(), value=name)

def toggle_character_active(name, active):
    """Toggle character active state."""
    char = load_character(name)
    if char:
        char["active"] = active
        path = os.path.join(CHARACTERS_DIR, f"{name}.json")
        with open(path, 'w') as f:
            json.dump(char, f, indent=2)
    return f"{'✅ Active' if active else '❌ Inactive'}: {name}"

def get_active_summary():
    """Get summary of active characters."""
    active = get_active_characters()
    if not active:
        return "No active characters"
    names = [str(c.get('name', 'Unknown')) for c in active if c and c.get('name') is not None]
    if not names:
        return "No active characters"
    return f"Active: {', '.join(names)}"

def set_active_characters_from_list(active_names):
    """Set active state for all characters based on the provided list."""
    all_chars = get_character_files()
    count = 0
    for name in all_chars:
        is_active = name in active_names
        char = load_character(name)
        if char:
            if char.get("active") != is_active:
                char["active"] = is_active
                path = os.path.join(CHARACTERS_DIR, f"{name}.json")
                with open(path, 'w') as f:
                    json.dump(char, f, indent=2)
                count += 1
    return f"Updated {count} characters"
