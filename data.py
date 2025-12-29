# data.py - Constants, defaults, and tag suggestions
import os

# --- FILE PATHS ---
CONFIG_FILE = "config.json"
GEN_CONFIG_FILE = "generation_config.json"
OUTPUT_DIR = "output"
CHARACTERS_DIR = "characters"
PRESETS_DIR = "presets"
STYLES_DIR = "styles"
TEMPLATES_DIR = "templates"
EXAMPLES_DIR = "examples"
LASTGEN_FILE = "_lastgen.json"

# Create directories
for d in [OUTPUT_DIR, CHARACTERS_DIR, PRESETS_DIR, STYLES_DIR, TEMPLATES_DIR, EXAMPLES_DIR, "inputs"]:
    if not os.path.exists(d):
        os.makedirs(d)

import shutil

def setup_examples():
    """Copy examples if folders are empty."""
    mapping = {
        "characters": os.path.join(EXAMPLES_DIR, "characters"),
        "styles": os.path.join(EXAMPLES_DIR, "styles"),
        "presets": os.path.join(EXAMPLES_DIR, "presets"),
        "templates": os.path.join(EXAMPLES_DIR, "templates"),
        "output": os.path.join(EXAMPLES_DIR, "output"),
        "config.json": os.path.join(EXAMPLES_DIR, "config.json"),
        "generation_config.json": os.path.join(EXAMPLES_DIR, "generation_config.json")
    }
    
    for target, source in mapping.items():
        if os.path.exists(source):
            if os.path.isdir(target):
                # Only copy if empty (ignoring .gitkeep)
                if not [f for f in os.listdir(target) if not f.startswith('.')]:
                    print(f"📦 Seeding {target} from examples...")
                    for item in os.listdir(source):
                        s = os.path.join(source, item)
                        d = os.path.join(target, item)
                        if os.path.isdir(s):
                            shutil.copytree(s, d)
                        else:
                            shutil.copy2(s, d)
            elif not os.path.exists(target):
                print(f"📦 Seeding {target} from examples...")
                shutil.copy2(source, target)

# --- MODEL CATEGORIES ---
MODEL_CATEGORIES = ["Illustrious", "Pony", "SDXL"]

# --- HEIGHT GUIDE (experimental) ---
# Multipliers for stretching template/pose images to create height variation
HEIGHT_GUIDES = {
    "very_tall": {"label": "Very Tall", "scale": 1.15},
    "tall": {"label": "Tall", "scale": 1.075},
    "average": {"label": "Average", "scale": 1.0},
    "small": {"label": "Small", "scale": 0.925},
    "very_small": {"label": "Very Small", "scale": 0.85}
}

# --- GENERATION MODES ---
GENERATION_MODES = ["txt2img", "img2img", "controlnet"]

# --- DEFAULTS ---
DEFAULT_CONFIG = {
    "api_url": "http://127.0.0.1:7860",
    "forge_path": "",
    "extra_args": "--api --listen --nowebui"
}

DEFAULT_GEN_CONFIG = {
    "model": "",
    "vae": "Automatic",
    "cfg_scale": 5,
    "width": 832,
    "height": 1216,
    "steps": 25,
    "sampler": "Euler a",
    "common_prompt": "score_9, score_8_up, score_7_up, masterpiece, best quality, detailed, highres, newest, recent, very as2, ",
    "common_negative": "poor quality, inflation, bad quality, worst quality, worst detail, censored, signature, watermark, text, lazyhand",
    "outfit_names": {
        "virtually_naked": "virtually naked",
        "fully_naked": "fully naked",
        "topless": "topless",
        "bottomless": "bottomless",
        "fully_clothed": "fully clothed",
        "full_underwear": "full underwear",
        "panties_only": "panties only",
        "bra_only": "bra only",
        "swimsuit": "swimsuit",
        "work": "work"
    },
    "morph_names": {
        "transformation": "transformation",
        "futa": "futa",
        "full_futa": "full futa",
        "pregnant": "pregnant",
        "male": "male",
        "female": "female",
        "trap": "trap"
    },
    "body_names": {
        "skin_color": "skin color",
        "eyes": "eyes",
        "head": "head",
        "hair_length": "hair length",
        "hair_color": "hair color",
        "breast": "breast",
        "nipples": "nipples",
        "abdomen": "abdomen",
        "back": "back",
        "ass": "ass",
        "pussy": "pussy",
        "anus": "anus",
        "penis": "penis",
        "legs": "legs",
        "feet": "feet",
        "hands_nails": "hands & nails",
        "armpits": "armpits",
        "tattoos": "tattoos",
        "jewelry": "jewelry"
    },
    "show_suggestions": True,
    "body_presets": {
        "full body front": ["skin_color", "eyes", "head", "hair_length", "hair_color", "breast", "nipples", "abdomen", "pussy", "penis", "legs", "feet", "hands_nails", "jewelry", "tattoos"],
        "full body back": ["skin_color", "hair_length", "hair_color", "back", "ass", "anus", "legs", "feet", "jewelry", "tattoos"],
        "portrait only": ["skin_color", "eyes", "head", "hair_length", "hair_color", "jewelry", "tattoos", "breast", "nipples"]
    },
    "set_prompt": "",
    "set_negative": "",
    "active_character_names": [],
    "active_outfits": ["virtually_naked"],
    "active_morphs": [],
    "active_body_parts": [],
    "active_styles": [],
    # Generation mode settings
    "generation_mode": "txt2img",
    # Img2Img settings
    "img2img_denoising": 0.75,
    "img2img_resize_mode": 0,  # 0=Just Resize, 1=Crop and Resize
    "img2img_template": "",
    "img2img_ignore_height_guide": False,
    # ControlNet settings (OpenPose only)
    "controlnet_pose": "",
    "controlnet_module": "openpose_full",
    "controlnet_model": "",
    "controlnet_weight": 1.0,
    "controlnet_control_mode": "ControlNet is more important",
    "controlnet_pixel_perfect": True,
    "controlnet_processor_res": 512,
    "controlnet_guidance_start": 0.0,
    "controlnet_guidance_end": 1.0,
    "merge_format": "webp",
    "add_date_prefix": True
}

DEFAULT_CHARACTER = {
    "name": "New Character",
    "positive": "",
    "negative": "",
    "outfits": {},
    "morphs": {},
    "body": {},
    "loras": [],
    "active": True,
    "height_guide": "average",
    "model_category": "Illustrious"
}

DEFAULT_STYLE = {
    "name": "New Style",
    "positive": "",
    "negative": "",
    "loras": [],
    "model_category": "Illustrious"
}

setup_examples()

# --- TAG SUGGESTIONS ---
TAG_SUGGESTIONS = {
    # BODY PARTS
    "skin_color": [
        "pale skin", "dark skin", "tan", "fair skin", "light brown skin",
        "brown skin", "olive skin", "white skin", "ebony", "tanned",
        "sun-kissed skin", "porcelain skin", "caramel skin"
    ],
    "eyes": [
        "blue eyes", "brown eyes", "green eyes", "red eyes", "golden eyes",
        "purple eyes", "pink eyes", "black eyes", "heterochromia", "slit pupils",
        "glowing eyes", "empty eyes", "closed eyes", "half-closed eyes",
        "wide eyes", "narrow eyes"
    ],
    "head": [
        "face", "smile", "open mouth", "tongue out", "licking lips",
        ":p", "blush", "flushed", "freckles", "mole under eye"
    ],
    "hair_length": [
        "short hair", "medium hair", "long hair", "very long hair",
        "absurdly long hair", "shoulder-length hair", "bob cut", "pixie cut",
        "bald", "buzz cut"
    ],
    "hair_color": [
        "black hair", "blonde hair", "brown hair", "white hair", "silver hair",
        "pink hair", "blue hair", "purple hair", "red hair", "green hair",
        "orange hair", "grey hair", "multicolored hair", "two-tone hair",
        "gradient hair", "streaked hair", "highlighted hair"
    ],
    "breast": [
        "flat chest", "small breasts", "medium breasts", "large breasts",
        "huge breasts", "gigantic breasts", "sagging breasts", "perky breasts",
        "cleavage", "sideboob", "underboob"
    ],
    "nipples": [
        "nipples", "areolae", "inverted nipples", "puffy nipples", "hard nipples"
    ],
    "abdomen": [
        "navel", "abs", "toned", "slim waist", "wide hips", "belly",
        "chubby", "plump", "fit", "muscular", "soft belly", "flat stomach",
        "hourglass figure", "curvy", "thicc"
    ],
    "back": [
        "back", "bare back", "arched back", "muscular back", "spine",
        "shoulder blades", "dimples of venus", "back muscles", "slim back"
    ],
    "ass": [
        "ass", "small ass", "large ass", "huge ass", "bubble butt",
        "round ass", "flat ass", "thong", "wedgie"
    ],
    "pussy": [
        "pussy", "shaved pussy", "pubic hair", "spread pussy", "cameltoe",
        "labia", "clit", "visible pussy"
    ],
    "anus": [
        "anus", "spread anus", "puckered anus", "gaping", "anal",
        "rosebud", "anus peek"
    ],
    "penis": [
        "penis", "large penis", "huge penis", "small penis",
        "flaccid", "veiny penis", "circumcised", "uncircumcised",
        "foreskin", "balls", "testicles"
    ],
    "legs": [
        "thick thighs", "slender legs", "long legs", "muscular legs",
        "thighhighs", "garter belt", "thigh gap", "cellulite"
    ],
    "feet": [
        "bare feet", "toes", "soles", "painted toenails",
        "high heels", "barefoot", "arched feet", "toe spread", "wrinkled soles"
    ],
    "hands_nails": [
        "hands", "slender fingers", "long nails", "painted nails", "manicure",
        "black nails", "red nails", "claw nails", "hand on hip", "hands up"
    ],
    "armpits": [
        "armpits", "armpit hair", "shaved armpits", "armpit focus",
        "underarm", "smooth armpits"
    ],
    "tattoos": [
        "tattoo", "tribal tattoo", "heart tattoo", "back tattoo", "arm tattoo",
        "shoulder tattoo", "thigh tattoo", "womb tattoo", "barcode tattoo",
        "tramp stamp", "full body tattoo", "sleeve tattoo"
    ],
    "jewelry": [
        "earrings", "necklace", "bracelet", "ring", "piercing", "choker",
        "collar", "anklet", "belly button piercing", "nipple piercing",
        "nose ring", "lip piercing", "ear piercing"
    ],
    # OUTFITS
    "virtually_naked": ["nude", "naked", "bare", "exposed", "undressed"],
    "fully_naked": ["completely nude", "full nude", "naked", "nudist", "naturist"],
    "topless": ["topless", "bare breasts", "no bra", "exposed breasts", "chest exposed"],
    "bottomless": ["bottomless", "no panties", "no underwear", "exposed pussy", "bare ass"],
    "fully_clothed": ["fully clothed", "dress", "uniform", "casual clothes", "formal wear"],
    "full_underwear": ["underwear", "bra and panties", "lingerie", "matching underwear", "lace underwear"],
    "panties_only": ["panties", "only panties", "topless panties", "bare breasts panties"],
    "bra_only": ["bra", "only bra", "bottomless bra", "sports bra", "lace bra"],
    "swimsuit": ["bikini", "one-piece swimsuit", "micro bikini", "thong bikini", "sling bikini", "string bikini"],
    # MORPHS
    "transformation": ["animal ears", "tail", "horns", "wings", "monster girl", "elf ears", "pointy ears", "demon girl", "angel"],
    "futa": ["futanari", "penis", "balls", "intersex", "dickgirl"],
    "full_futa": ["futanari", "pussy", "large penis", "huge balls", "erection", "veiny cock"],
    "pregnant": ["pregnant", "belly", "huge belly", "lactation", "birth", "knocked up"],
    "male": ["1boy", "male focus", "muscular male", "bara", "masculine", "manly"],
    "female": ["1girl", "female focus", "solo female", "feminine", "girly", "womanly"],
    "trap": ["crossdressing", "trap", "feminine male", "otoko no ko", "girly male", "androgynous"],
}

# --- CONSTANTS ---
COMMON_PORTS = [7860, 7861, 7862, 7863, 7864, 7865]

SDXL_SIZES = [
    (1024, 1024), (1152, 896), (896, 1152),
    (1216, 832), (832, 1216), (1344, 768), (768, 1344),
    (1536, 640), (640, 1536)
]
