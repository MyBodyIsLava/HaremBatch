# config.py - Configuration load/save and helper functions
import os
import json

from data import (
    CONFIG_FILE, GEN_CONFIG_FILE,
    DEFAULT_CONFIG, DEFAULT_GEN_CONFIG, TAG_SUGGESTIONS,
    HEIGHT_GUIDES, GENERATION_MODES, LASTGEN_FILE
)

_CONFIG_CACHE = None
_GEN_CONFIG_CACHE = None

def clear_config_caches():
    global _CONFIG_CACHE, _GEN_CONFIG_CACHE
    _CONFIG_CACHE = None
    _GEN_CONFIG_CACHE = None

def load_config():
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE
    
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            res = {**DEFAULT_CONFIG, **json.load(f)}
    else:
        res = DEFAULT_CONFIG.copy()
    
    _CONFIG_CACHE = res
    return res

def load_gen_config():
    global _GEN_CONFIG_CACHE
    if _GEN_CONFIG_CACHE is not None:
        return _GEN_CONFIG_CACHE
    
    if os.path.exists(GEN_CONFIG_FILE):
        try:
            with open(GEN_CONFIG_FILE, 'r') as f:
                loaded = json.load(f)
                # Merge top level
                config = {**DEFAULT_GEN_CONFIG, **loaded}
                
                # Smart merge for names to prevent old numeric keys from taking over if new ones are present
                for key in ["outfit_names", "morph_names", "body_names"]:
                     if key in loaded and isinstance(loaded[key], dict):
                          config[key] = loaded[key] # Trust the loaded dict if exists
                
                # Merge body_presets: Keep user's, add defaults if missing
                user_presets = config.get("body_presets", {})
                default_presets = DEFAULT_GEN_CONFIG["body_presets"]
                for k, v in default_presets.items():
                    if k not in user_presets:
                        user_presets[k] = v
                config["body_presets"] = user_presets

                # Sanitize image paths
                for img_key in ["img2img_template", "controlnet_pose"]:
                    if config.get(img_key) and not os.path.exists(config[img_key]):
                        config[img_key] = None
                
                _GEN_CONFIG_CACHE = config
                return config
        except (json.JSONDecodeError, OSError) as e:
            print(f"⚠️ Error loading generation config: {e}. Using defaults.")
            _GEN_CONFIG_CACHE = DEFAULT_GEN_CONFIG.copy()
            return _GEN_CONFIG_CACHE
            
    _GEN_CONFIG_CACHE = DEFAULT_GEN_CONFIG.copy()
    return _GEN_CONFIG_CACHE

def save_config(api_url, forge_path, extra_args, save_metadata=True):
    config = {"api_url": api_url, "forge_path": forge_path, "extra_args": extra_args, "save_metadata": save_metadata}
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    clear_config_caches()
    return "✅ Configuration saved!"

def save_gen_config(config_dict=None, **kwargs):
    config = load_gen_config()
    
    # Update from config_dict if provided (new way)
    if config_dict and isinstance(config_dict, dict):
        # We need to handle special cases like None means empty, etc.
        # But generally we trust the dict.
        # Filter keys that are valid config keys
        valid_keys = config.keys()
        for k, v in config_dict.items():
             config[k] = v
             
    # Update from kwargs (legacy way + partial updates)
    for k, v in kwargs.items():
        if v is not None:
             config[k] = v
        # Special handling for clearing values
        elif k in ["img2img_template", "controlnet_pose"]:
             config[k] = ""
             
    # Handle text inputs for names if they are in kwargs (from UI)
    outfits_text = kwargs.get("outfits_text")
    if outfits_text is not None:
        outfit_names = {}
        for line in outfits_text.strip().split('\n'):
            if ':' in line:
                key, name = line.split(':', 1)
                outfit_names[key.strip()] = name.strip()
        config["outfit_names"] = outfit_names

    morphs_text = kwargs.get("morphs_text")
    if morphs_text is not None:
        morph_names = {}
        for line in morphs_text.strip().split('\n'):
            if ':' in line:
                key, name = line.split(':', 1)
                morph_names[key.strip()] = name.strip()
        config["morph_names"] = morph_names

    body_text = kwargs.get("body_text")
    if body_text is not None:
        body_names = {}
        for line in body_text.strip().split('\n'):
            if ':' in line:
                key, name = line.split(':', 1)
                body_names[key.strip()] = name.strip()
        
        # Ensure default body parts stay
        for key, name in DEFAULT_GEN_CONFIG["body_names"].items():
            if key not in body_names:
                body_names[key] = name
                
        config["body_names"] = body_names
    
    with open(GEN_CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    clear_config_caches()
    return "✅ Settings saved!"

def save_lastgen(config_dict):
    """Save last used generation settings."""
    with open(LASTGEN_FILE, 'w') as f:
        json.dump(config_dict, f, indent=2)

def load_lastgen():
    """Load last used generation settings."""
    if os.path.exists(LASTGEN_FILE):
        with open(LASTGEN_FILE, 'r') as f:
            return json.load(f)
    return None

def add_config_entry(category, entry_text):
    """Add a new entry to config (outfit, morph or body)."""
    if ':' not in entry_text:
        return f"❌ Invalid format. Use 'key_name: Display Name'"
    
    key, name = entry_text.split(':', 1)
    key = key.strip().lower().replace(' ', '_')
    name = name.strip()
    
    if not key or not name:
        return "❌ Key or Name cannot be empty"
        
    config = load_gen_config()
    if category == "outfit":
        config.setdefault("outfit_names", {})[key] = name
    elif category == "morph":
        config.setdefault("morph_names", {})[key] = name
    else:
        config.setdefault("body_names", {})[key] = name
        
    with open(GEN_CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    clear_config_caches()
    return f"✅ Added {category} '{name}'"

# --- GETTERS ---

def get_body_names_text():
    gen_cfg = load_gen_config()
    body_names = gen_cfg.get("body_names", DEFAULT_GEN_CONFIG["body_names"])
    return "\n".join([f"{k}: {v}" for k, v in body_names.items()])

def get_body_choices():
    gen_cfg = load_gen_config()
    body_names = gen_cfg.get("body_names", DEFAULT_GEN_CONFIG["body_names"])
    return [(v, k) for k, v in body_names.items()]

def get_all_body_keys():
    gen_cfg = load_gen_config()
    body_names = gen_cfg.get("body_names", DEFAULT_GEN_CONFIG["body_names"])
    return list(body_names.keys())

def get_body_display_name(key):
    gen_cfg = load_gen_config()
    body_names = gen_cfg.get("body_names", DEFAULT_GEN_CONFIG["body_names"])
    return body_names.get(str(key), key)

def get_suggestions_for_key(key):
    return TAG_SUGGESTIONS.get(key, [])

def should_show_suggestions():
    gen_cfg = load_gen_config()
    return gen_cfg.get("show_suggestions", True)

def append_tag(current_text, tag):
    if current_text and current_text.strip():
        return f"{current_text.strip()}, {tag}"
    return tag

def save_show_suggestions(value):
    config = load_gen_config()
    config["show_suggestions"] = value
    with open(GEN_CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    clear_config_caches()
    return "✅ Suggestion setting saved! Refresh page to apply."

def get_outfit_names_text():
    gen_cfg = load_gen_config()
    outfit_names = gen_cfg.get("outfit_names", DEFAULT_GEN_CONFIG["outfit_names"])
    return "\n".join([f"{k}: {v}" for k, v in outfit_names.items()])

def get_morph_names_text():
    gen_cfg = load_gen_config()
    morph_names = gen_cfg.get("morph_names", DEFAULT_GEN_CONFIG["morph_names"])
    return "\n".join([f"{k}: {v}" for k, v in morph_names.items()])

def get_outfit_choices():
    gen_cfg = load_gen_config()
    outfit_names = gen_cfg.get("outfit_names", DEFAULT_GEN_CONFIG["outfit_names"])
    return [(v, k) for k, v in outfit_names.items()]

def get_morph_choices():
    gen_cfg = load_gen_config()
    morph_names = gen_cfg.get("morph_names", DEFAULT_GEN_CONFIG["morph_names"])
    return [(v, k) for k, v in morph_names.items()]

def get_all_outfit_keys():
    gen_cfg = load_gen_config()
    outfit_names = gen_cfg.get("outfit_names", DEFAULT_GEN_CONFIG["outfit_names"])
    return list(outfit_names.keys())

def get_all_morph_keys():
    gen_cfg = load_gen_config()
    morph_names = gen_cfg.get("morph_names", DEFAULT_GEN_CONFIG["morph_names"])
    return list(morph_names.keys())

def get_outfit_display_name(key):
    gen_cfg = load_gen_config()
    outfit_names = gen_cfg.get("outfit_names", DEFAULT_GEN_CONFIG["outfit_names"])
    return outfit_names.get(str(key), key)

def get_morph_display_name(key):
    gen_cfg = load_gen_config()
    morph_names = gen_cfg.get("morph_names", DEFAULT_GEN_CONFIG["morph_names"])
    return morph_names.get(str(key), key)

def get_style_choices():
    from styles import get_style_files
    return get_style_files()

# --- HEIGHT GUIDE HELPERS ---

def get_height_guide_choices():
    """Return list of (display_name, key) tuples for height guide dropdown."""
    return [(v["label"], k) for k, v in HEIGHT_GUIDES.items()]

def get_height_guide_keys():
    """Return list of height guide keys."""
    return list(HEIGHT_GUIDES.keys())

def get_height_guide_label(key):
    """Get display label for a height guide key."""
    return HEIGHT_GUIDES.get(key, {}).get("label", "Average")

def get_height_guide_scale(key):
    """Get the scale multiplier for a height guide key."""
    return HEIGHT_GUIDES.get(key, {}).get("scale", 1.0)

def get_generation_mode_choices():
    """Return list of generation mode choices."""
    return GENERATION_MODES
