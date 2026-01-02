import os
import json
import time
import shutil
from data import OUTPUT_DIR
from PIL import Image

# Ensure output directory exists
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def get_set_path(set_name):
    """Get the directory path for a set."""
    return os.path.join(OUTPUT_DIR, set_name)

def get_set_json_path(set_name):
    """Get the path to the set.json file."""
    return os.path.join(get_set_path(set_name), "set.json")

def list_sets():
    """List all available sets in the output directory."""
    sets = []
    if not os.path.exists(OUTPUT_DIR):
        return []
        
    for name in os.listdir(OUTPUT_DIR):
        path = os.path.join(OUTPUT_DIR, name)
        if os.path.isdir(path) and os.path.exists(os.path.join(path, "set.json")):
            sets.append(name)
            
    # Sort by creation time (newest first)
    sets.sort(key=lambda x: os.path.getctime(os.path.join(OUTPUT_DIR, x)), reverse=True)
    return sets

def create_set(base_name, gen_config, active_characters, set_prompt="", set_negative=""):
    """Create a new set directory and metadata file."""
    # Ensure unique name
    set_name = base_name
    counter = 1
    while os.path.exists(get_set_path(set_name)):
        set_name = f"{base_name}_{counter}"
        counter += 1
    
    set_path = get_set_path(set_name)
    os.makedirs(set_path)
    os.makedirs(os.path.join(set_path, "_old"), exist_ok=True)
    
    set_data = {
        "name": set_name,
        "created_at": int(time.time()),
        "layout": "frieze",
        "order": "ltr",
        "gen_config": gen_config,
        "characters": active_characters, # List of character dicts or names
        "set_prompt": set_prompt,
        "set_negative": set_negative,
        "images": [] # List of {filename, char_name, params}
    }
    
    save_set(set_name, set_data)
    return set_name, set_data

def save_set(set_name, set_data):
    """Save set metadata to json."""
    with open(get_set_json_path(set_name), 'w') as f:
        json.dump(set_data, f, indent=2)

def load_set(set_name):
    """Load set metadata."""
    path = get_set_json_path(set_name)
    if not os.path.exists(path):
        return None
    
    with open(path, 'r') as f:
        return json.load(f)

def prepare_set_image_path(set_name, char_name):
    """
    Prepare the path for a new image.
    If an image for the character exists, move it to _old.
    Returns the target path for the new image.
    """
    set_path = get_set_path(set_name)
    old_path = os.path.join(set_path, "_old")
    if not os.path.exists(old_path):
        os.makedirs(old_path)
    
    # Clean char name for filename
    safe_name = "".join(c for c in char_name if c.isalnum() or c in "._- ")
    filename = f"{safe_name}.png"
    target_path = os.path.join(set_path, filename)
    
    if os.path.exists(target_path):
        # Move existing to _old with timestamp
        timestamp = int(time.time())
        old_filename = f"{safe_name}_{timestamp}.png"
        shutil.move(target_path, os.path.join(old_path, old_filename))
        
    return target_path, filename

def add_image_to_set(set_name, filename, char_name, params=None):
    """
    Register an image in the set. 
    Note: 'filename' here is the basename in the set folder.
    """
    set_data = load_set(set_name)
    if not set_data:
        return False
        
    # Check if character already has an entry, if so update it, otherwise append
    # But user wants 'frieze' which is ordered. 
    # Usually we generate for all characters.
    # If we regenerate, we update the specific entry.
    # If we simple add (like new generation), we might be adding a new character or updating existing.
    
    # Let's see if we have an entry for this character/filename
    found = False
    for img in set_data["images"]:
        if img["char_name"] == char_name:
            img["filename"] = filename
            img["params"] = params or {}
            found = True
            break
            
    if not found:
        image_entry = {
            "filename": filename,
            "char_name": char_name,
            "params": params or {}
        }
        set_data["images"].append(image_entry)
        
    save_set(set_name, set_data)
    return True

def delete_image_from_set(set_name, index):
    """Delete an image from the set at the given index. Moves file to _old."""
    set_data = load_set(set_name)
    if not set_data or index < 0 or index >= len(set_data["images"]):
        return False, "❌ Invalid index"
    
    img_entry = set_data["images"][index]
    char_name = img_entry["char_name"]
    filename = img_entry["filename"]
    
    set_path = get_set_path(set_name)
    file_path = os.path.join(set_path, filename)
    old_path = os.path.join(set_path, "_old")
    
    # Move file to _old if it exists
    if os.path.exists(file_path):
        os.makedirs(old_path, exist_ok=True)
        timestamp = int(time.time())
        old_filename = f"{os.path.splitext(filename)[0]}_{timestamp}{os.path.splitext(filename)[1]}"
        shutil.move(file_path, os.path.join(old_path, old_filename))
    
    # Remove from set data
    set_data["images"].pop(index)
    save_set(set_name, set_data)
    
    return True, f"🗑️ Removed {char_name}"

def replace_image_in_set(set_name, index, new_file_path):
    """Replace an image in the set with a new file. Moves old to _old."""
    if not new_file_path:
        return False
        
    set_data = load_set(set_name)
    if not set_data or index < 0 or index >= len(set_data["images"]):
        return False
        
    img_entry = set_data["images"][index]
    char_name = img_entry["char_name"]
    
    # Prepare target path (this moves existing to _old)
    target_path, filename = prepare_set_image_path(set_name, char_name)
    
    # Copy new file to target
    shutil.copy(new_file_path, target_path)
    
    # Update entry
    img_entry["filename"] = filename
    # Remove params as it's no longer generated with stored params
    img_entry["params"] = {}
    
    save_set(set_name, set_data)
    return True

def move_image(set_name, index, direction):
    """Move image at index 'left' (-1) or 'right' (+1)."""
    set_data = load_set(set_name)
    if not set_data:
        return None
        
    images = set_data["images"]
    new_index = index + direction
    
    if 0 <= new_index < len(images):
        images[index], images[new_index] = images[new_index], images[index]
        save_set(set_name, set_data)
        return new_index
    
    return index

def delete_set(set_name):
    """Delete a set and its directory."""
    path = get_set_path(set_name)
    if os.path.exists(path):
        shutil.rmtree(path)
        return True
    return False

def merge_set_images(set_name, overlap=0, fmt="webp"):
    """Merge all images in the set into a single frieze image."""
    from PIL import Image
    
    set_data = load_set(set_name)
    if not set_data or not set_data["images"]:
        return None, "No images to merge"
        
    images_paths = []
    set_path = get_set_path(set_name)
    
    for img_entry in set_data["images"]:
        p = os.path.join(set_path, img_entry["filename"])
        if os.path.exists(p):
            images_paths.append(p)
            
    if not images_paths:
        return None, "No valid images found"
        
    try:
        images = [Image.open(p).convert("RGBA") for p in images_paths]
        
        # Calculate total width with overlap
        total_width = sum(img.width for img in images) - (len(images) - 1) * overlap
        max_height = max(img.height for img in images)
        
        # Ensure at least 1 pixel width
        total_width = max(1, total_width)
        
        merged_img = Image.new('RGBA', (total_width, max_height), (0, 0, 0, 0))
        
        x_offset = 0
        for img in images:
            merged_img.paste(img, (x_offset, 0), img)
            x_offset += img.width - overlap
            
        timestamp = int(time.time())
        ext = "webp" if fmt == "webp" else "png"
        filename = f"00_HaremBatch_{timestamp}.{ext}"
        save_path = os.path.join(set_path, filename)
        
        if fmt == "webp":
            # Lossless=True is good, but for mass images, Lossy Q95 might be even better
            # Let's go with Lossless for now as it's safer for transparency, or Q95
            merged_img.save(save_path, quality=95, method=6) # Method 6 is slowest/best compression
        else:
            merged_img.save(save_path, optimize=True, compress_level=9)
        
        return save_path, f"Merge complete: {filename}"
        
    except Exception as e:
        return None, f"Merge failed: {str(e)}"

def safe_flood_fill(image, xy, value, threshold=0):
    """
    Flood fills the image with the given value starting from xy.
    Uses PIL.ImageDraw.floodfill if available, or a custom implementation.
    
    Args:
        image: PIL Image object (RGBA)
        xy: (x, y) start coordinate
        value: Fill value (e.g. (0,0,0,0) for transparency)
        threshold: Tolerance/threshold for color matching (0-255)
    """
    from PIL import ImageDraw
    
    # Try using PIL's native floodfill (Pillow >= 8.0)
    if hasattr(ImageDraw, "floodfill"):
        ImageDraw.floodfill(image, xy, value, thresh=threshold)
        return image
        
    # Fallback to simple pixel replacement if floodfill not available or fails (unlikely)
    # But user specifically asked for "adjacent", so simple replace is bad.
    # We really should count on Pillow having floodfill.
    return image

def remove_background_from_set(set_name, threshold=10, contiguous=True):
    """
    Remove solid background color from all images in the set.
    Non-destructive: Saves original as *.source.png if not exists, 
    and always processes from source.
    """
    import numpy as np
    
    set_data = load_set(set_name)
    if not set_data or not set_data["images"]:
        return None, "No images to process"
        
    set_path = get_set_path(set_name)
    processed_count = 0
    
    for img_entry in set_data["images"]:
        filename = img_entry["filename"]
        file_path = os.path.join(set_path, filename)
        
        # Source file path (e.g. image.png -> image.source.png)
        source_filename = os.path.splitext(filename)[0] + ".source.png"
        source_path = os.path.join(set_path, source_filename)
        
        if not os.path.exists(file_path):
            continue
            
        # 1. Ensure source file exists
        if not os.path.exists(source_path):
            try:
                shutil.copy(file_path, source_path)
            except Exception as e:
                print(f"Error creating source backup for {filename}: {e}")
                continue
                
        try:
            # 2. Open SOURCE image for processing
            img = Image.open(source_path).convert("RGBA")
            # Convert to numpy array
            arr = np.array(img)
            
            # Get corners to determine background color
            height, width = arr.shape[:2]
            corners = [
                arr[0, 0],
                arr[0, width - 1],
                arr[height - 1, 0],
                arr[height - 1, width - 1]
            ]
            
            # Find a non-transparent corner as reference
            ref_bg = corners[0]
            if ref_bg[3] == 0:
                for c in corners:
                    if c[3] > 0:
                        ref_bg = c
                        break
                        
            # If reference is transparent, maybe the whole background is already transparent?
            # But we proceed with the logic. 
            
            # Calculate color distance vectorised
            # Only consider RGB lines (not Alpha) for distance if contiguous=False or for ref matching
            # But for simplicity, let's use RGB distance
            
            # Extract RGB
            img_rgb = arr[:, :, :3].astype(float)
            ref_rgb = ref_bg[:3].astype(float)
            
            # Euclidean distance: sqrt(sum((x-y)^2))
            # optimization: use sum of squared differences and compare to threshold^2
            diff = img_rgb - ref_rgb
            dist_sq = np.sum(diff**2, axis=2)
            threshold_sq = threshold ** 2
            
            mask = dist_sq <= threshold_sq
            
            # Handle alpha - existing alpha should be preserved? 
            # Or if pixel matches background, we set alpha to 0
            
            if contiguous:
                # For contiguous, we need safe_flood_fill logic which is hard to vectorise efficiently without cv2
                # But we can try a simple approximate: use PIL floodfill only on the mask?
                # Actually, PIL floodfill is faster than python loop but slower than numpy global replace
                # If user wants "contiguous=True" (default), we should stick to PIL Floodfill if available
                # or use cv2.floodFill if cv2 is installed.
                # Since we want to fix "performance bottleneck", and simple floodfill in PIL is written in C,
                # the previous implementation's slowness was the Python loop around it OR the custom loop fallback.
                # The previous code had:
                # if contiguous:
                #    ... safe_flood_fill ...
                # else:
                #    ... python loop ...
                # So the Python loop was only in the NON-contiguous case?
                # Wait, looking at previous code:
                # if contiguous: 
                #    loop over corners -> safe_flood_fill
                # else: 
                #    loop over data -> python calc
                
                # So contiguous was likely fast enough IF ImageDraw.floodfill exists.
                # The non-contiguous was O(N) in python.
                
                # Let's optimize non-contiguous with numpy, 
                # And for contiguous, rely on PIL (it's C) but ensure no python loop pixel access.
                pass
                
                # However, the user said "For a batch of 4K images, this function will freeze the app."
                # If they are using contiguous (default), verify safe_flood_fill isn't falling back to something slow.
                # safe_flood_fill in original code checks `hasattr(ImageDraw, "floodfill")`.
                
                # Let's assume we want to speed up everything.
                # For contiguous, we can't easily use simple numpy masking. 
                # But we can use skimage or cv2 if available. 
                # Without them, PIL floodfill is best bet.
                
                from PIL import ImageDraw
                if hasattr(ImageDraw, "floodfill"):
                     # PIL Floodfill is efficient.
                     # Only need to be sure we don't do python loop stuff.
                     # The original code did `if dist <= threshold * 1.5:` inside the corner loop? 
                     # No, it calculated distance for the corner to ref_bg in python (fast, just 4 pixels)
                     # Then called floodfill.
                     
                     # So maybe the bottleneck IS non-contiguous mode or the fact users use non-contiguous?
                     # OR the user thinks the whole function is slow.
                     
                     # Let's implement the NumPy Masking for NON-contiguous (which was slow).
                     # And for contiguous, we keep PIL.
                     
                     # Actually, let's look at the corner logic again.
                     # The original code:
                     # if contiguous:
                     #    for i, corner in enumerate(corners):
                     #       ...
                     #       dist = color_distance(...)
                     #       if dist <= threshold * 1.5:
                     #            safe_flood_fill(...)
                     
                     ImageDraw.floodfill(img, (0,0), (0,0,0,0), thresh=threshold)
                     # We need to do this for all valid corners.
                     
                     # BUT to be "tactical" and fix the "Python loop" complaint specifically:
                     # "It iterates over pixels using Python loops (for item in data: inside color_distance)."
                     # That specific loop was in the `else` (non-contiguous) block.
                     
                     if contiguous:
                          # Use PIL Floodfill
                          # We iterate 4 corners - that's fine.
                          corner_coords = [(0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)]
                          visited_colors = set()
                          for xy in corner_coords:
                               c_color = img.getpixel(xy)
                               if c_color[3] == 0: continue # Already transparent
                               
                               # Check distance to ref_bg
                               c_rgb = np.array(c_color[:3], dtype=float)
                               ref_rgb = np.array(ref_bg[:3], dtype=float)
                               dist = np.sqrt(np.sum((c_rgb - ref_rgb)**2))
                               
                               if dist <= threshold * 2.0: # lenient for corners
                                   if hasattr(ImageDraw, "floodfill"):
                                       ImageDraw.floodfill(img, xy, (0,0,0,0), thresh=threshold)
            else:
                # Vectorized Non-Contiguous
                # Set alpha to 0 where mask is True
                arr[mask, 3] = 0
                img = Image.fromarray(arr)
        
            # 3. Save to DISPLAY filename (original filename)
            img.save(file_path, "PNG")
            processed_count += 1
        
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            
    return processed_count, f"Processed {processed_count} images."

def restore_background_from_set(set_name):
    """
    Revert background removal by restoring images from their *.source.png backups.
    """
    import shutil
    
    set_data = load_set(set_name)
    if not set_data or not set_data["images"]:
        return 0, "No images found."
        
    set_path = get_set_path(set_name)
    restored_count = 0
    
    for img_entry in set_data["images"]:
        filename = img_entry["filename"]
        file_path = os.path.join(set_path, filename)
        source_filename = os.path.splitext(filename)[0] + ".source.png"
        source_path = os.path.join(set_path, source_filename)
        
        if os.path.exists(source_path):
            try:
                shutil.copy(source_path, file_path)
                restored_count += 1
            except Exception as e:
                print(f"Error restoring background for {filename}: {e}")
                
    return restored_count, f"✅ Restored {restored_count} images from source backups."

def rename_set(old_name, new_name):
    """Rename a set directory and update its metadata."""
    if not old_name or not new_name:
        return False, "❌ Invalid names"
    
    new_name = new_name.strip()
    if old_name == new_name:
        return True, "✅ Name unchanged"

    old_path = get_set_path(old_name)
    new_path = get_set_path(new_name)

    if not os.path.exists(old_path):
        return False, "❌ Original set not found"
    
    if os.path.exists(new_path):
        return False, f"❌ Set '{new_name}' already exists"
    
    try:
        os.rename(old_path, new_path)
        
        # Update metadata
        # We can't use load_set(old_name) anymore because path changed
        json_path = os.path.join(new_path, "set.json")
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                data = json.load(f)
            data["name"] = new_name
            with open(json_path, 'w') as f:
                json.dump(data, f, indent=2)
                
        return True, f"✅ Renamed to '{new_name}'"
    except Exception as e:
        return False, f"❌ Rename failed: {str(e)}"

def flip_image(set_name, index):
    """Flip the image at the given index left-to-right."""
    from PIL import Image
    set_data = load_set(set_name)
    if not set_data or index < 0 or index >= len(set_data["images"]):
        return False, "❌ Invalid index"
    
    img_entry = set_data["images"][index]
    set_path = get_set_path(set_name)
    file_path = os.path.join(set_path, img_entry["filename"])
    
    if not os.path.exists(file_path):
        return False, "❌ Image file missing"
        
    try:
        img = Image.open(file_path)
        flipped = img.transpose(Image.FLIP_LEFT_RIGHT)
        flipped.save(file_path)
        return True, "✅ Image flipped"
    except Exception as e:
        return False, f"❌ Flip failed: {str(e)}"
