# generation.py - Batch generation logic
import os
import time
import base64
import requests
import json
from PIL import Image, PngImagePlugin
from io import BytesIO

from data import OUTPUT_DIR, HEIGHT_GUIDES
from config import load_config, load_gen_config, get_height_guide_scale
from forge import find_forge
from sets import create_set, get_set_path, add_image_to_set, prepare_set_image_path
from characters import get_active_characters
import characters # specific import for loading by name
import shutil

# --- GLOBAL STOP FLAG ---
def request_stop_generation():
    """Signal generation to stop."""
    from data import GEN_STATE
    GEN_STATE.stop()
    return "🛑 Stop requested..."
def encode_pil_to_base64(image):
    """Convert a PIL Image to a base64 string."""
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

# --- IMAGE HELPERS FOR IMG2IMG / CONTROLNET ---

def load_image_as_base64(image_path):
    """Load an image file and return as base64 string."""
    if not image_path or not os.path.exists(image_path):
        return None
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def load_and_scale_image_on_canvas(image_path, canvas_width, canvas_height, scale_factor=1.0):
    """
    Load image, scale its height by scale_factor, and paste it onto a fixed canvas.
    Alignment is BOTTOM-CENTER (or just stretched width, bottom aligned).
    
    If scale_factor < 1.0 (e.g. 0.85): Character is shorter, empty space at TOP.
    If scale_factor > 1.0 (e.g. 1.15): Character is taller, cropped at TOP (or scaled up).
    
    Actually, height guide is usually about "relative height".
    If we assume the template fills the canvas at 1.0 scale.
    
    New logic:
    1. Resize input image to (canvas_width, int(canvas_height * scale_factor))
    2. Create canvas (canvas_width, canvas_height)
    3. Paste resized image at bottom: (0, canvas_height - resized_height)
    """
    if not image_path or not os.path.exists(image_path):
        return None, None
    
    try:
        img = Image.open(image_path)
        original_size = img.size
        
        # Calculate target dimensions for the CONTENT
        target_content_width = int(canvas_width)
        target_content_height = int(canvas_height * scale_factor)
        
        # Resize content (LANCZOS for quality)
        img_resized = img.resize((target_content_width, target_content_height), Image.LANCZOS)
        
        # Create Canvas
        # For ControlNet (OpenPose), black background is standard.
        # For Img2Img, we probably want to match the top pixel or transparent?
        # Let's assume RGB black for now as it's safest for OpenPose.
        # If input is RGBA, we can preserve alpha.
        canvas_mode = "RGBA" if img.mode == "RGBA" else "RGB"
        bg_color = (0, 0, 0, 0) if canvas_mode == "RGBA" else (0, 0, 0)
        
        canvas = Image.new(canvas_mode, (int(canvas_width), int(canvas_height)), bg_color)
        
        # Align Bottom
        paste_y = int(canvas_height) - target_content_height
        canvas.paste(img_resized, (0, paste_y))
        
        # Convert to base64
        buffer = BytesIO()
        canvas.save(buffer, format="PNG")
        base64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        return base64_str, original_size
    except Exception as e:
        print(f"Error processing image: {e}")
        return None, None

def calculate_char_dimensions(base_width, base_height, height_guide_key, ignore_height_guide=False):
    """Calculate character-specific dimensions based on height guide.
    
    Height guide scales the HEIGHT while keeping WIDTH constant.
    This creates the illusion of different character heights.
    """
    if ignore_height_guide:
        return base_width, base_height
    
    scale = get_height_guide_scale(height_guide_key)
    # Scale height only - taller characters have more height
    new_height = int(base_height * scale)
    return base_width, new_height

def build_controlnet_args(pose_base64, module, model, weight, control_mode="ControlNet is more important", pixel_perfect=True, processor_res=512, guidance_start=0, guidance_end=1):
    """Build ControlNet args for the alwayson_scripts payload.
    
    API Reference: https://github.com/Mikubill/sd-webui-controlnet/wiki/API
    """
    if not pose_base64:
        print("[CONTROLNET] WARNING: pose_base64 is empty!")
    
    is_lllite = model and "lllite" in model.lower()
    
    cn_args = {
        "image": pose_base64,  # Base64 encoded image (NOT input_image!)
        "enabled": True,
        "module": module or "dw_openpose_full",
        "model": model or "None",
        "weight": float(weight) if weight is not None else 1.0,
        "resize_mode": "Just Resize",  # String, not int!
        "control_mode": control_mode,  # Use passed control_mode
        "pixel_perfect": pixel_perfect,
        "processor_res": int(processor_res) if processor_res else 512,
        "threshold_a": 64,
        "threshold_b": 64,
        "guidance_start": float(guidance_start),
        "guidance_end": float(guidance_end),
    }
    
    print(f"[CONTROLNET] model={model.split()[0] if model else 'None'}, weight={weight}, mode='{control_mode}', res={processor_res if not pixel_perfect else 'Auto'}, {'LLLite' if is_lllite else 'Standard'}")
    
    return {"controlnet": {"args": [cn_args]}}

def extract_infotext(api_response):
    """Extract standard SD metadata (infotext) from API response."""
    try:
        if 'info' in api_response:
            info_data = json.loads(api_response['info'])
            if 'infotexts' in info_data and info_data['infotexts']:
                return info_data['infotexts'][0]
            return api_response['info']
    except:
        pass
    return ""

def switch_model(api_url, model_name):
    """Switch to a different model."""
    if not model_name:
        return True
    try:
        options = requests.get(f"{api_url}/sdapi/v1/options", timeout=10).json()
        if options.get("sd_model_checkpoint") == model_name:
            return True
        
        response = requests.post(
            f"{api_url}/sdapi/v1/options",
            json={"sd_model_checkpoint": model_name},
            timeout=120
        )
        return response.status_code == 200
    except:
        return False

def process_batch(prompt, neg_prompt, count):
    online, api_url = find_forge()
    gen_cfg = load_gen_config()
    
    if not online:
        yield None, "❌ Forge is OFFLINE"
        return
        
    cfg = load_config()
    should_save_metadata = cfg.get("save_metadata", True)
    
    yield None, f"🟢 Connected to {api_url}"
    
    if gen_cfg["model"]:
        yield None, f"🔄 Loading model: {gen_cfg['model']}..."
        if not switch_model(api_url, gen_cfg["model"]):
            yield None, f"⚠️ Could not switch model, using current"
    
    full_prompt = f"{gen_cfg['common_prompt']}, {prompt}" if gen_cfg['common_prompt'] else prompt
    full_negative = f"{gen_cfg['common_negative']}, {neg_prompt}" if gen_cfg['common_negative'] else neg_prompt
    
    generated_images = []
    
    for i in range(int(count)):
        yield (generated_images[-1] if generated_images else None), f"Generating image {i+1}/{count}..."
        
        payload = {
            "prompt": full_prompt,
            "negative_prompt": full_negative,
            "steps": gen_cfg["steps"],
            "cfg_scale": gen_cfg["cfg_scale"],
            "width": gen_cfg["width"],
            "height": gen_cfg["height"],
            "sampler_name": gen_cfg["sampler"]
        }
        
        try:
            response = requests.post(f"{api_url}/sdapi/v1/txt2img", json=payload)
            if response.status_code == 200:
                r = response.json()
                image_data = base64.b64decode(r['images'][0])
                image = Image.open(BytesIO(image_data))
                
                # Prepare Metadata
                pnginfo = PngImagePlugin.PngInfo()
                if should_save_metadata:
                    metadata_text = extract_infotext(r)
                    if metadata_text:
                        pnginfo.add_text("parameters", metadata_text)
                
                timestamp = int(time.time())
                filename = os.path.join(OUTPUT_DIR, f"img_{timestamp}_{i}.png")
                image.save(filename, pnginfo=pnginfo)
                
                generated_images.append(filename)
                yield filename, f"Image {i+1} done."
            else:
                yield (generated_images[-1] if generated_images else None), f"API Error: {response.text}"
                
        except Exception as e:
            yield (generated_images[-1] if generated_images else None), f"Error: {str(e)}"

    yield (generated_images[-1] if generated_images else None), "✅ Batch complete!"

def apply_tag_removals(base_prompt, modifier_prompt):
    """Apply -"TAG" removals from modifier to base prompt."""
    if not modifier_prompt:
        return base_prompt, ""
    
    tags_to_remove = []
    clean_modifiers = []
    
    for part in modifier_prompt.split(','):
        part = part.strip()
        if part.startswith('-') and len(part) > 1:
            tag = part[1:].strip()
            if (tag.startswith('"') and tag.endswith('"')) or (tag.startswith("'") and tag.endswith("'")):
                tag = tag[1:-1].strip()
            
            if tag:
                tags_to_remove.append(tag.lower())
        elif part:
            clean_modifiers.append(part)
    
    if tags_to_remove and base_prompt:
        base_parts = [p.strip() for p in base_prompt.split(',')]
        filtered_parts = [p for p in base_parts if p.lower() not in tags_to_remove]
        base_prompt = ', '.join(filtered_parts)
    
    return base_prompt, ', '.join(clean_modifiers)

def generate_characters_batch(
    outfit_keys, morph_keys, body_keys=[], style_names=[], 
    set_name_input=None, active_character_names=None, set_prompt="", set_negative="",
    generation_mode="txt2img",
    template_image=None, denoising_strength=0.75, ignore_height_guide=False,
    pose_image=None, cn_module="dw_openpose_full", cn_model="", cn_weight=1.0,
    cn_control_mode="ControlNet is more important", cn_pixel_perfect=True, cn_processor_res=512,
    cn_guidance_start=0.0, cn_guidance_end=1.0
):
    """Generate one image for each active character with selected outfits, morphs, body parts and styles.
    
    Supports three generation modes:
    - txt2img: Standard text-to-image generation (default)
    - img2img: Uses template_image as init, applies height guide stretching
    - controlnet: Uses pose_image for OpenPose control
    """
    online, api_url = find_forge()
    gen_cfg = load_gen_config()
    from styles import load_style
    from data import GEN_STATE
    
    # Reset stop flag at start of batch
    GEN_STATE.reset()
    
    # Determine active characters
    if active_character_names:
        # If specific list provided (e.g. from Order Queue), use it
        # We need to load the full character data for these names
        all_chars = characters.get_character_files() # Names
        active_chars = []
        # Parse input if string (from TextArea) or list
        if isinstance(active_character_names, str):
            names = [n.strip() for n in active_character_names.split('\n') if n.strip()]
        else:
            names = active_character_names
            
        for name in names:
            if name in all_chars:
                c_data = characters.load_character(name)
                if c_data:
                    active_chars.append(c_data)
    else:
        # Fallback to backend active status
        active_chars = get_active_characters()
    
    cfg = load_config()
    should_save_metadata = cfg.get("save_metadata", True)
    
    if not online:
        yield None, "❌ Forge is OFFLINE"
        return
    
    if not active_chars:
        yield None, "❌ No active characters"
        return
    
    # Mode-specific validation
    if generation_mode == "img2img" and not template_image:
        yield None, "❌ img2img mode requires a template image"
        return
    
    if generation_mode == "controlnet" and not pose_image:
        yield None, "❌ ControlNet mode requires a pose image"
        return
    
    mode_emoji = {
        "txt2img": "📝",
        "img2img": "🖼️",
        "controlnet": "🎮"
    }
    yield None, f"🟢 Connected - {len(active_chars)} characters [{mode_emoji.get(generation_mode, '')} {generation_mode}]"
    
    if gen_cfg["model"]:
        yield None, f"🔄 Loading model: {gen_cfg['model']}..."
        if not switch_model(api_url, gen_cfg["model"]):
            yield None, f"⚠️ Could not switch model, using current"
    
    # Initialize Set
    set_name = None
    if set_name_input is not None:
        timestamp_str = time.strftime("%Y%m%d_%H%M%S")
        
        prefix = ""
        if gen_cfg.get("add_date_prefix", True):
            prefix = time.strftime("%y%m%d_%H%M ") # YYMMDD_HHMM
            
        base_name = set_name_input.strip()
        if not base_name:
            # Try to use prompt
            if set_prompt and set_prompt.strip():
                # Take first a few words, alphanumeric only
                # Remove common tags or special characters
                clean_prompt = "".join(c if c.isalnum() or c == " " else " " for c in set_prompt)
                words = [w for w in clean_prompt.split() if w]
                base_name = " ".join(words[:4]).strip()
            
            if not base_name:
                base_name = f"Batch_{timestamp_str}"
        
        # Combine prefix and base name, then make safe for filesystem
        combined_name = f"{prefix}{base_name}".strip()
        set_name = "".join(c for c in combined_name if c.isalnum() or c in "._- ").strip()
        
        if not set_name:
             set_name = f"Batch_{timestamp_str}"
        
        if set_name:
            if not os.path.exists(get_set_path(set_name)):
                set_name, set_data = create_set(set_name, gen_cfg, [c["name"] for c in active_chars], set_prompt=set_prompt, set_negative=set_negative)
                yield None, f"📁 Created set: {set_name}"
                
            # --- Save Inputs (Future Proofing) ---
            # Save the template or pose image to the set folder for reference
            set_path = get_set_path(set_name)
            inputs_dir = os.path.join(set_path, "inputs")
            os.makedirs(inputs_dir, exist_ok=True)
            
            if generation_mode == "img2img" and template_image:
                try:
                    # template_image is a filepath (str) from Gradio
                    shutil.copy(template_image, os.path.join(inputs_dir, "template.png"))
                except Exception as e:
                    print(f"Failed to archive template image: {e}")
                    
            if generation_mode == "controlnet" and pose_image:
                try:
                    shutil.copy(pose_image, os.path.join(inputs_dir, "pose.png"))
                except Exception as e:
                    print(f"Failed to archive pose image: {e}")
            # --------------------------------------
                
            # Re-fetch path just in case we are adding to existing
            # (This line was part of the provided snippet, but get_set_path(set_name) is called above)
            # set_path = get_set_path(set_name)
    
    generated_images = []
    
    # Load Styles
    loaded_styles = []
    if style_names:
        for sn in style_names:
            style = load_style(sn)
            if style:
                loaded_styles.append(style)
    
    # --- MODEL CATEGORY CHECK ---
    # Collate all categories involved
    all_categories = {} # name -> category
    for char in active_chars:
        all_categories[char["name"]] = char.get("model_category", "Illustrious")
    for style in loaded_styles:
        all_categories[f"Style: {style['name']}"] = style.get("model_category", "Illustrious")
    
    unique_cats = set(all_categories.values())
    if len(unique_cats) > 1:
        warning_msg = "⚠️ **Model Category Mismatch!** Some items use different model types:\n"
        for cat in unique_cats:
            items = [name for name, c in all_categories.items() if c == cat]
            warning_msg += f"- **{cat}**: {', '.join(items)}\n"
        warning_msg += "\nGeneration proceed, but quality may be affected."
        yield None, warning_msg
        time.sleep(2) # Give user time to read
    # ---------------------------
    
    # Pre-load template/pose images for reuse
    base_width = gen_cfg["width"]
    base_height = gen_cfg["height"]

    print(f"DEBUG: Active chars count: {len(active_chars)}, mode: {generation_mode}")
    for i, char in enumerate(active_chars):
        # --- CANCELLATION CHECK ---
        if GEN_STATE.should_stop:
            yield (generated_images[-1] if generated_images else None), "🛑 Generation Cancelled!"
            # Cleanup if a set was created and we want to stop fully? 
            # User asked to "remove file generate" -> remove all generated images for this batch
            yield None, "🧹 Cleaning up generated files..."
            
            # Delete generated images
            for img_path in generated_images:
                if os.path.exists(img_path):
                    try:
                        os.remove(img_path)
                    except:
                        pass
            
            # If set mode, maybe delete the set folder if it's new and empty?
            # But we might have just added images to an existing set.
            # If 'set_name' was created NEW in this session, we might want to delete it.
            # But checking if we just created it is tricky unless we track it.
            # For now, let's just delete the images we just made.
            # If the set becomes empty, we could delete it, but that's safer.
            
            if set_name:
                from sets import delete_set, load_set
                # Reload set to check if it has other images
                s_data = load_set(set_name)
                # If we deleted all images we just added, and the set has no other images
                # (or we can just blindly call delete_set if we created it new)
                # Simpler approach: If the user cancels a "batch", they likely want the whole batch gone.
                # If we created a new set for this batch, request_stop_generation logic implies full abort.
                
                # Check if set is empty after image deletion
                # (images were physically deleted above, but are still in set.json)
                # We need to update set.json to remove them or just delete the set logic.
                
                # Re-reading user request: "cancel the set and remove file generate"
                # implying the whole set should be nuked if we were making one.
                if set_name_input: # If we were creating a named/new set
                     delete_set(set_name)
                     yield None, f"🗑️ Set '{set_name}' deleted."
            
            yield None, "❌ Cancelled and Cleaned up."
            return

        char_name = char["name"]
        height_guide_key = char.get("height_guide", "average")
        print(f"DEBUG: Processing char {i+1}: {char_name} (height_guide: {height_guide_key})")
        
        # Calculate scale factor
        scale_factor = 1.0
        if generation_mode in ["img2img", "controlnet"] and not ignore_height_guide:
             scale_factor = get_height_guide_scale(height_guide_key)
        
        # Fixed canvas dimensions (user wants image size to stay same)
        char_width = base_width
        char_height = base_height # API payload always uses base height now
        
        
        # Start with common prompts as the absolute base
        current_positive = gen_cfg.get("common_prompt", "")
        current_negative = gen_cfg.get("common_negative", "")
        
        def extract_pn(data):
            if isinstance(data, str): return data, ""
            return data.get("positive", ""), data.get("negative", "")
            
        def apply_layer(layer_pos, layer_neg):
             nonlocal current_positive, current_negative
             # Apply removals from this layer to current state
             current_positive, layer_pos_clean = apply_tag_removals(current_positive, layer_pos)
             current_negative, layer_neg_clean = apply_tag_removals(current_negative, layer_neg)
             
             # Append clean additions
             if layer_pos_clean:
                 current_positive = f"{current_positive}, {layer_pos_clean}" if current_positive else layer_pos_clean
             if layer_neg_clean:
                 current_negative = f"{current_negative}, {layer_neg_clean}" if current_negative else layer_neg_clean

        # 1. Character Base
        apply_layer(char.get("positive", ""), char.get("negative", ""))

        # 2. Body Parts
        for bk in body_keys:
             p, n = extract_pn(char.get("body", {}).get(bk, {}))
             apply_layer(p, n)
             
        # 3. Morphs
        for mk in morph_keys:
             p, n = extract_pn(char.get("morphs", {}).get(mk, {}))
             apply_layer(p, n)

        # 4. Outfits
        for ok in outfit_keys:
             p, n = extract_pn(char.get("outfits", {}).get(ok, {}))
             apply_layer(p, n)
        
        # 5. Styles
        for s in loaded_styles:
            apply_layer(s.get("positive", ""), s.get("negative", ""))
            
        # 6. Set Prompts
        if set_prompt or set_negative:
             apply_layer(set_prompt or "", set_negative or "")

        char_positive = current_positive
        char_negative = current_negative
        
        # We no longer prepend common prompts here because they are handled in the accumulator
        full_prompt = char_positive
        full_negative = char_negative
        
        height_label = HEIGHT_GUIDES.get(height_guide_key, {}).get("label", "Average")
        yield (generated_images[-1] if generated_images else None), f"Generating {char_name} [{height_label}] ({i+1}/{len(active_chars)})..."
        
        # Sanitize prompts (remove newlines primarily)
        full_prompt = full_prompt.replace('\n', ' ').replace('\r', ' ')
        full_negative = full_negative.replace('\n', ' ').replace('\r', ' ')
        
        # Build base payload
        payload = {
            "prompt": full_prompt,
            "negative_prompt": full_negative,
            "steps": gen_cfg["steps"],
            "cfg_scale": gen_cfg["cfg_scale"],
            "width": char_width,
            "height": char_height,
            "sampler_name": gen_cfg["sampler"]
        }
        
        # Mode-specific payload modifications
        endpoint = "txt2img"
        
        if generation_mode == "img2img":
            endpoint = "img2img"
            # Load and scale template on fixed canvas
            template_b64, original_size = load_and_scale_image_on_canvas(template_image, char_width, char_height, scale_factor)
            if template_b64:
                payload["init_images"] = [template_b64]
                payload["denoising_strength"] = denoising_strength
                payload["resize_mode"] = 0  # Just Resize (we pre-formatted it)
                
                # Metadata helper: store mode info but maybe not the huge b64
                payload["_generation_mode"] = "img2img"
                payload["_scale_factor"] = scale_factor
            else:
                yield (generated_images[-1] if generated_images else None), f"⚠️ {char_name}: Could not load template image"
                continue
                
        elif generation_mode == "controlnet":
            endpoint = "txt2img"
            pose_b64, original_size = load_and_scale_image_on_canvas(pose_image, char_width, char_height, scale_factor)
            if pose_b64:
                payload["alwayson_scripts"] = build_controlnet_args(
                    pose_b64, cn_module, cn_model, cn_weight, cn_control_mode,
                    cn_pixel_perfect, cn_processor_res, cn_guidance_start, cn_guidance_end
                )
                payload["_generation_mode"] = "controlnet"
                payload["_scale_factor"] = scale_factor
            else:
                yield (generated_images[-1] if generated_images else None), f"⚠️ {char_name}: Could not load pose image"
                continue
        
        try:
            print(f"📝 Prompt: {payload['prompt']}")
            print(f"📝 Negative: {payload['negative_prompt']}")
            
            response = requests.post(f"{api_url}/sdapi/v1/{endpoint}", json=payload)
            if response.status_code == 200:
                r = response.json()
                
                image_data = base64.b64decode(r['images'][0])
                image = Image.open(BytesIO(image_data))
                
                timestamp = int(time.time())
                safe_name = "".join(c for c in char_name if c.isalnum() or c in "._- ")
                outfit_id = "_".join(outfit_keys) if outfit_keys else ""
                
                print(f"🎨 Generated: {char_name} (Outfit: {outfit_id or 'Default'})")
                morph_id = "_".join(morph_keys) if morph_keys else ""
                filename_parts = [safe_name]
                if outfit_id: filename_parts.append(outfit_id)
                if morph_id: filename_parts.append(morph_id)
                filename_parts.append(str(timestamp))
                
                # Prepare Metadata
                pnginfo = PngImagePlugin.PngInfo()
                if should_save_metadata:
                    metadata_text = extract_infotext(r)
                    if metadata_text:
                        pnginfo.add_text("parameters", metadata_text)
                
                if set_name:
                    # Sets Mode: Use fixed naming with versioning
                    target_path, clean_filename = prepare_set_image_path(set_name, char_name)
                    image.save(target_path, pnginfo=pnginfo)
                    
                    # Strip huge base64 before saving to JSON meta
                    clean_params = payload.copy()
                    if "init_images" in clean_params:
                        del clean_params["init_images"]
                    if "alwayson_scripts" in clean_params and "controlnet" in clean_params["alwayson_scripts"]:
                         # We keep ControlNet args but strip the image
                         cn_args = clean_params["alwayson_scripts"]["controlnet"]["args"]
                         if cn_args:
                             cn_args[0]["image"] = "" # Strip huge b64
                    
                    add_image_to_set(set_name, clean_filename, char_name, clean_params)
                    filename = target_path
                else:
                    # Legacy/Simple Mode: Timestamped filenames
                    filename = os.path.join(OUTPUT_DIR, f"{'_'.join(filename_parts)}.png")
                    image.save(filename, pnginfo=pnginfo)
                
                generated_images.append(filename)
                yield filename, f"✅ {char_name} done."
            else:
                try:
                    error_details = response.json()
                except:
                    error_details = response.text
                yield (generated_images[-1] if generated_images else None), f"❌ {char_name} failed: {response.status_code} - {error_details}"
                
        except Exception as e:
            yield (generated_images[-1] if generated_images else None), f"❌ {char_name} error: {str(e)}"

    yield (generated_images[-1] if generated_images else None), f"✅ Batch complete! {len(generated_images)}/{len(active_chars)} images"

def regenerate_set_image(set_name, image_index, nudge_params=None):
    """
    Regenerate a specific image in a set using its stored parameters but new seed.
    nudge_params: dict with keys 'prompt', 'negative', 'strength', 'source_image'
    """
    online, api_url = find_forge()
    from sets import load_set, prepare_set_image_path, add_image_to_set
    
    if not online:
        yield "❌ Forge is OFFLINE"
        return
        
    cfg = load_config()
    should_save_metadata = cfg.get("save_metadata", True)
        
    set_data = load_set(set_name)
    if not set_data:
        yield "❌ Set not found"
        return
            
    try:
        image_index = int(image_index)
        if image_index < 0 or image_index >= len(set_data["images"]):
            yield "❌ Invalid image index"
            return
            
        img_entry = set_data["images"][image_index]
        payload = img_entry.get("params", {}).copy()
        
        if not payload:
            yield "❌ No params found for this image"
            return
            
        # --- ROBUST INPUT RESTORATION ---
        # If the original was img2img or controlnet, try to reload from archived inputs/
        gen_mode = payload.get("_generation_mode")
        scale_f = payload.get("_scale_factor", 1.0)
        
        set_path = get_set_path(set_name)
        inputs_dir = os.path.join(set_path, "inputs")
        
        input_dir = os.path.join(set_path, "inputs")

        try:
            # Load current config to force recent ControlNet settings
            gen_cfg = load_gen_config()
            
            # Override payload params with current global settings if they exist
            # This ensures resolution, pixel perfect, etc. are applied even if old image didn't have them
            current_cn_pixel_perfect = gen_cfg.get("controlnet_pixel_perfect", True)
            current_cn_res = gen_cfg.get("controlnet_processor_res", 512)
            current_cn_guidance_start = gen_cfg.get("controlnet_guidance_start", 0.0)
            current_cn_guidance_end = gen_cfg.get("controlnet_guidance_end", 1.0)
            current_cn_mode = gen_cfg.get("controlnet_control_mode", "ControlNet is more important")
        except:
            print("Failed to load current config for regeneration override.")
            current_cn_pixel_perfect = True
            current_cn_res = 512
            current_cn_guidance_start = 0.0
            current_cn_guidance_end = 1.0
            current_cn_mode = "ControlNet is more important"
        
        if gen_mode == "img2img":
            archive_path = os.path.join(inputs_dir, "template.png")
            if os.path.exists(archive_path):
                yield f"📦 Loading archived template for {img_entry['char_name']}..."
                # Re-calculate dimensions from original params
                w, h = payload.get("width", 832), payload.get("height", 1216)
                img_b64, _ = load_and_scale_image_on_canvas(archive_path, w, h, scale_f)
                if img_b64:
                    payload["init_images"] = [img_b64]
                    payload["resize_mode"] = 0
            

        elif gen_mode == "controlnet":
            archive_path = os.path.join(inputs_dir, "pose.png")
            if os.path.exists(archive_path):
                yield f"📦 Loading archived pose for {img_entry['char_name']}..."
                w, h = payload.get("width", 832), payload.get("height", 1216)
                img_b64, _ = load_and_scale_image_on_canvas(archive_path, w, h, scale_f)
                if img_b64:
                    # Update existing scripts or create new
                    if "alwayson_scripts" not in payload: payload["alwayson_scripts"] = {}
                    if "controlnet" not in payload["alwayson_scripts"]:
                         # We'll need some default model/module if missing, but usually it's in payload
                         cn_model = "None"
                         cn_module = "openpose_full"
                         cn_weight = 1.0
                    else:
                         # Use existing ones from payload
                         args = payload["alwayson_scripts"]["controlnet"]["args"][0]
                         cn_model = args.get("model", "None")
                         cn_module = args.get("module", "openpose_full")
                         cn_weight = args.get("weight", 1.0)
                         
                    payload["alwayson_scripts"] = build_controlnet_args(
                        img_b64, cn_module, cn_model, cn_weight,
                        control_mode=current_cn_mode,
                        pixel_perfect=current_cn_pixel_perfect,
                        processor_res=current_cn_res,
                        guidance_start=current_cn_guidance_start,
                        guidance_end=current_cn_guidance_end
                    )

        # --- Nudge Logic ---
        if nudge_params:
            extra_pos = nudge_params.get("prompt", "").strip()
            extra_neg = nudge_params.get("negative", "").strip()
            
            if extra_pos:
                payload["prompt"] = f"{extra_pos}, {payload['prompt']}"
            if extra_neg:
                payload["negative_prompt"] = f"{extra_neg}, {payload['negative_prompt']}"
                
            # 2. Source Image Override (Loopback / Img2Img switch)
            source_img = nudge_params.get("source_image")
            if source_img:
                if isinstance(source_img, str): # path
                    source_img = Image.open(source_img)
                
                # If we convert to img2img, we need init_images
                payload["init_images"] = [encode_pil_to_base64(source_img)]
                
                # Use provided strength
                strength = nudge_params.get("strength")
                if strength is not None:
                    payload["denoising_strength"] = float(strength)
                
                payload["resize_mode"] = 0
                payload["_generation_mode"] = "img2img"
            
            else:
                # No new image, but maybe strength adjustment for existing img2img/controlnet?
                strength = nudge_params.get("strength")
                if strength is not None:
                    # If it was img2img
                    if "init_images" in payload:
                         payload["denoising_strength"] = float(strength)
                    # If controlnet
                    elif "alwayson_scripts" in payload and "controlnet" in payload["alwayson_scripts"]:
                        # Update weight of first unit
                         args = payload["alwayson_scripts"]["controlnet"]["args"]
                         if args and len(args) > 0:
                             args[0]["weight"] = float(strength)

        # Determine endpoint based on payload content
        endpoint_name = "txt2img"
        if "init_images" in payload:
            endpoint_name = "img2img"
        
        endpoint_url = f"{api_url}/sdapi/v1/{endpoint_name}"
        
        # --- CUMULATIVE COMMON PROMPTS (from feedback) ---
        # Add current session's common prompts if they aren't already represented
        # We prepend them for priority.
        gen_cfg = load_gen_config()
        cp = gen_cfg.get("common_prompt", "").strip()
        cn = gen_cfg.get("common_negative", "").strip()
        
        if cp and cp not in payload["prompt"]:
             payload["prompt"] = f"{cp}, {payload['prompt']}"
        if cn and cn not in payload["negative_prompt"]:
             payload["negative_prompt"] = f"{cn}, {payload['negative_prompt']}"
        
        # Update Seed
        payload["seed"] = -1
        
        yield None, f"🔄 Regenerating {img_entry['char_name']}..."
        
        # Call API
        print(f"📝 Prompt: {payload['prompt']}")
        print(f"📝 Negative: {payload['negative_prompt']}")
        
        response = requests.post(endpoint_url, json=payload)
        
        if response.status_code == 200:
            r = response.json()
            image_b64 = r['images'][0]
            image = Image.open(BytesIO(base64.b64decode(image_b64)))
            
            # Save Metadata
            pnginfo = PngImagePlugin.PngInfo()
            if should_save_metadata:
                metadata_text = extract_infotext(r)
                if metadata_text:
                    pnginfo.add_text("parameters", metadata_text)
            
            # Save (Overwriting old image logic or new version? Set editor usually updates in place or moves old)
            # prepare_set_image_path moves old to _old
            target_path, clean_filename = prepare_set_image_path(set_name, img_entry["char_name"])
            image.save(target_path, pnginfo=pnginfo)
            
            print(f"✅ Regenerated: {img_entry['char_name']}")
            yield None, f"✅ {img_entry['char_name']} regenerated!"
            
        else:
            yield None, f"❌ Failed: {response.status_code}"
            
    except Exception as e:
        yield None, f"❌ Error: {str(e)}"

def generate_variant(
    set_name, image_index, similarity=0.9, 
    prompt_override=None, negative_override=None
):
    """
    Generate a variant (Image B) from an existing set image (Image A).
    similarity: 0.0 to 1.0 (1.0 = identical, 0.9 = 10% change)
    """
    online, api_url = find_forge()
    from sets import load_set
    
    if not online:
        yield None, "❌ Forge is OFFLINE"
        return

    set_data = load_set(set_name)
    if not set_data:
        yield None, "❌ Set not found"
        return

    try:
        image_index = int(image_index)
        if image_index < 0 or image_index >= len(set_data["images"]):
            yield None, "❌ Invalid image index"
            return
            
        img_entry = set_data["images"][image_index]
        payload = img_entry.get("params", {}).copy()
        
        # Load Source Image (A)
        set_path = get_set_path(set_name)
        img_path = os.path.join(set_path, img_entry["filename"])
        
        if not os.path.exists(img_path):
             yield None, "❌ Source image missing"
             return
             
        # img2img setup
        # Strip ControlNet/AlwaysOnScripts as they cause base64 issues and are redundant for variant generation (img2img holds structure)
        if "alwayson_scripts" in payload:
            del payload["alwayson_scripts"]

        source_b64 = load_image_as_base64(img_path)
        with Image.open(img_path) as tmp_img:
            payload["width"] = tmp_img.width
            payload["height"] = tmp_img.height
            
        payload["init_images"] = [source_b64]
        payload["resize_mode"] = 0 
        
        # Calculate Denoising Strength
        # Similarity 1.0 -> Denoising 0.0
        # Similarity 0.9 -> Denoising 0.1
        # Similarity 0.0 -> Denoising 1.0
        denoising = 1.0 - max(0.0, min(1.0, float(similarity)))
        payload["denoising_strength"] = denoising
        
        # Update Prompts if overrides provided
        if prompt_override:
            payload["prompt"] = prompt_override
        if negative_override:
            payload["negative_prompt"] = negative_override
            
        # New Seed
        payload["seed"] = -1
        
        # Call API
        endpoint_url = f"{api_url}/sdapi/v1/img2img"
        
        yield None, f"🎨 Generating variant ({int(similarity*100)}% similarity)..."
        
        response = requests.post(endpoint_url, json=payload)
        
        if response.status_code == 200:
            r = response.json()
            image_b64 = r['images'][0]
            
            # Save to temporary file for preview
            # Storing in set's _old directory as requested
            base_dir = os.path.join(get_set_path(set_name), "_old")
            os.makedirs(base_dir, exist_ok=True)
            
            temp_filename = f"ab_variant_{int(time.time())}.png"
            temp_path = os.path.join(base_dir, temp_filename)
            
            image = Image.open(BytesIO(base64.b64decode(image_b64)))
            
            # Prepare Metadata
            pnginfo = PngImagePlugin.PngInfo()
            metadata_text = extract_infotext(r)
            if metadata_text:
                pnginfo.add_text("parameters", metadata_text)
                
            image.save(temp_path, pnginfo=pnginfo)
            
            yield temp_path, "✅ Variant generated"
            
        else:
            yield None, f"❌ Failed: {response.status_code}"

    except Exception as e:
        yield None, f"❌ Error: {str(e)}"
