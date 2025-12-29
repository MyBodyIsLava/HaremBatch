import gradio as gr
import os
import time
import shutil
from PIL import Image

# Import from modules
from data import SDXL_SIZES, HEIGHT_GUIDES, GENERATION_MODES, MODEL_CATEGORIES, DEFAULT_GEN_CONFIG
from config import (
    load_config, load_gen_config, save_config, save_gen_config, add_config_entry,
    get_outfit_names_text, get_morph_names_text, get_body_names_text,
    get_outfit_choices, get_morph_choices, get_body_choices, get_style_choices,
    get_all_outfit_keys, get_all_morph_keys, get_all_body_keys,
    get_outfit_display_name, get_morph_display_name, get_body_display_name,
    get_suggestions_for_key, should_show_suggestions, append_tag, save_show_suggestions,
    load_lastgen, save_lastgen
)
from forge import (
    get_models_list, get_vae_list, get_samplers_list,
    refresh_dropdowns, refresh_status,
    launch_forge, kill_all_forge, find_forge,
    get_controlnet_models, get_controlnet_modules
)
from characters import (
    get_character_files, load_character, save_character_from_ui,
    delete_character, rename_character,
    get_active_characters, get_active_summary,
    get_preset_files, save_preset, load_preset, delete_preset,
    load_character_ui, create_new_character, toggle_character_active,
    get_body_presets, save_body_preset, load_body_preset, delete_body_preset,
    activate_all_characters, deactivate_all_characters,
    set_active_characters_from_list, get_generated_presets
)
from styles import (
    get_style_files, load_style, save_style, delete_style, load_style_ui,
    create_new_style
)
from generation import process_batch, generate_characters_batch, regenerate_set_image, generate_variant
from sets import list_sets, load_set, move_image, replace_image_in_set, get_set_path, merge_set_images, delete_set, remove_background_from_set, restore_background_from_set, rename_set, prepare_set_image_path, add_image_to_set
from generation import request_stop_generation


# --- INTERFACE ---

config = load_config()
gen_config = load_gen_config()

# --- HELPERS ---

def sync_checks_to_order(selected_list, current_order_text):
    """When checkboxes change, update order text."""
    # Parse current order
    current_order = [line.strip() for line in current_order_text.split('\n') if line.strip()]
    selected_set = set(selected_list)
    
    # Remove items no longer selected
    new_order = [name for name in current_order if name in selected_set]
    
    # Add new items that were not in order (append to end)
    current_set = set(current_order)
    for name in selected_list:
        if name not in current_set:
            new_order.append(name)
            
    return "\n".join(new_order)

def load_preset_with_name(name):
    msg, active = load_preset(name)
    # Don't populate save name for generated presets
    generated = get_generated_presets()
    safe_name = name if name not in generated and name != "All Characters" else ""
    # active is the list of names
    order_text = "\n".join(active)
    return msg, active, safe_name, order_text

def inc_trigger(curr):
    return curr + 1

def get_latest_set_preview():
    """Returns the path of the last image from the most recently created generation set."""
    try:
        sets = list_sets()
        if not sets:
            return None
        latest_set = sets[0]
        set_data = load_set(latest_set)
        if not set_data or not set_data.get("images"):
            return None
        set_path = get_set_path(latest_set)
        # Return the last image in the set
        return os.path.join(set_path, set_data["images"][-1]["filename"])
    except Exception as e:
        return None

def stabilize_image(path, filename):
    """Copy temporary gradio images to a stable local directory."""
    if not path or not os.path.exists(path):
        return None
    
    # If already in project directory, don't copy
    abs_path = os.path.abspath(path)
    if abs_path.startswith(os.getcwd()):
        return path
        
    dest_dir = "inputs"
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, f"{filename}.png")
    
    try:
        if abs_path != os.path.abspath(dest_path):
            shutil.copy2(path, dest_path)
        return dest_path
    except Exception as e:
        print(f"⚠️ Failed to stabilize image {path}: {e}")
        return path

def preload_session():
    """Load settings from _lastgen.json if it exists."""
    lastgen = load_lastgen()
    
    # Needs to match session_inputs order specifically (32 fields):
    if not lastgen:
        return [gr.update() for _ in range(32)]
    
    results = [
        lastgen.get("model", gr.update()),
        lastgen.get("vae", gr.update()),
        lastgen.get("cfg_scale", gr.update()),
        lastgen.get("width", gr.update()),
        lastgen.get("height", gr.update()),
        lastgen.get("steps", gr.update()),
        lastgen.get("sampler", gr.update()),
        lastgen.get("common_prompt", gr.update()),
        lastgen.get("common_negative", gr.update()),
        lastgen.get("active_outfits", gr.update()),
        lastgen.get("active_morphs", gr.update()),
        lastgen.get("active_body_parts", gr.update()),
        [s for s in lastgen.get("active_styles", []) if s in get_style_choices()] if "active_styles" in lastgen else gr.update(),
        lastgen.get("set_prompt", gr.update()),
        lastgen.get("set_negative", gr.update()),
        "\n".join(lastgen.get("active_character_names", [])) if "active_character_names" in lastgen else gr.update(),
        lastgen.get("generation_mode", gr.update()),
        lastgen.get("img2img_template") if lastgen.get("img2img_template") and os.path.exists(lastgen.get("img2img_template")) else None if "img2img_template" in lastgen else gr.update(),
        lastgen.get("img2img_denoising", gr.update()),
        lastgen.get("img2img_ignore_height_guide", gr.update()),
        lastgen.get("controlnet_pose") if lastgen.get("controlnet_pose") and os.path.exists(lastgen.get("controlnet_pose")) else None if "controlnet_pose" in lastgen else gr.update(),
        lastgen.get("controlnet_module", gr.update()),
        lastgen.get("controlnet_model", gr.update()),
        lastgen.get("controlnet_weight", gr.update()),
        lastgen.get("controlnet_control_mode", gr.update()),
        lastgen.get("controlnet_pixel_perfect", gr.update()),
        lastgen.get("controlnet_processor_res", gr.update()),
        lastgen.get("controlnet_guidance_start", gr.update()),
        lastgen.get("controlnet_guidance_end", gr.update()),
        lastgen.get("show_suggestions", gr.update()),
        lastgen.get("add_date_prefix", gr.update()),
        lastgen.get("merge_format", gr.update())
    ]
    return results

def move_image_left(set_name, idx):
    from sets import move_image
    move_image(set_name, idx, -1)

def move_image_right(set_name, idx):
    from sets import move_image
    move_image(set_name, idx, 1)

def flip_image_wrapper(set_name, idx):
    from sets import flip_image
    return flip_image(set_name, idx)

def replace_image_wrapper(set_name, idx, file_obj):
    from sets import replace_image_in_set
    if file_obj:
        replace_image_in_set(set_name, idx, file_obj.name)

def on_generation_complete():
    sets = list_sets()
    latest = sets[0] if sets else None
    gr.Info("✅ Generation set complete!")
    return gr.update(choices=sets, value=latest)

css = """
#frieze_container {
    overflow-x: auto;
    flex-wrap: nowrap !important;
}
.frieze_column {
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
}
.frieze_column img {
    width: 100% !important;
    height: auto !important;
    max-height: none !important;
    object-fit: contain;
}
.frieze_column > div, .frieze_column .gradio-image, .frieze_column .image-container {
    width: 100% !important;
    max-width: none !important;
    height: auto !important;
}
.frieze_button_row {
    gap: 2px !important;
    margin-top: 2px !important;
}
.frieze_button_row button, .frieze_button_row .gradio-button {
    min-width: 0px !important;
    flex: 1 !important;
    padding-left: 2px !important;
    padding-right: 2px !important;
    font-size: 0.75em !important;
}
"""

with gr.Blocks(title="HaremBatch UI") as ui:
    gr.Markdown("## 🚀 HaremBatch")
    
    with gr.Tabs(elem_id="main_tabs") as tabs:
        with gr.Tab("Generation"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 🎭 Character Batch")
                    gr.Markdown("Character Preset")
                    with gr.Row():
                        dd_preset_main = gr.Dropdown(
                            show_label=False,
                            choices=get_generated_presets() + get_preset_files(), 
                            value="All characters" if "All Characters" in get_generated_presets() else (get_generated_presets()[0] if get_generated_presets() else None),
                            scale=10,
                            info="Choose a character preset to load into the queue."
                        )
                        btn_refresh_presets_main = gr.Button("🔄", scale=0, min_width=40)
                    
                    with gr.Row():
                        with gr.Column(scale=1):
                            txt_set_name_main = gr.Textbox(label="Set Name (Optional)", placeholder="New Set Name", info="Used for the output folder name.")
                            chk_add_date = gr.Checkbox(label="Add Date Prefix", value=gen_config.get("add_date_prefix", True), info="YYYYMMDD_HHMM prefix.")
                        txt_set_prompt = gr.Textbox(label="Set Prompt (Added to all)", value=gen_config.get("set_prompt", ""), placeholder="beach background, sunset", scale=2, info="Poses, scene details, lighting.")
                        txt_set_negative = gr.Textbox(label="Set Negative (Added to all)", value=gen_config.get("set_negative", ""), placeholder="indoors, crowd", scale=2, info="Things to avoid in this batch.")
                    
                    with gr.Row():
                        dd_body_main = gr.Dropdown(
                            label="Body Parts",
                            choices=get_body_choices(),
                            multiselect=True,
                            value=gen_config.get("active_body_parts", []),
                            scale=4,
                            info="Select which body parts to show."
                        )
                    with gr.Row():
                        _body_presets = get_body_presets()
                        dd_body_preset = gr.Dropdown(
                            label="Body Preset",
                            choices=_body_presets,
                            value=None,
                            allow_custom_value=False,
                            scale=3,
                            info="Load a saved set of body parts."
                        )
                        txt_body_preset_save_as = gr.Textbox(label="Save As", placeholder="Full Detail", scale=2)
                        with gr.Column(scale=0, min_width=50):
                            btn_save_body_preset = gr.Button("💾", size="sm")
                            btn_delete_body_preset = gr.Button("🗑️", size="sm")
                    with gr.Row():
                        _outfit_choices = get_outfit_choices()
                        dd_outfits_main = gr.Dropdown(
                            label="Outfits",
                            choices=_outfit_choices,
                            multiselect=True,
                            value=gen_config.get("active_outfits", ["virtually_naked"] if any(c[1] == "virtually_naked" for c in _outfit_choices) else []),
                            scale=3,
                            info="Select outfits to generate."
                        )
                        dd_morphs_main = gr.Dropdown(
                            label="Morphs",
                            choices=get_morph_choices(),
                            multiselect=True,
                            value=gen_config.get("active_morphs", []),
                            scale=3,
                            info="Select body transformations."
                        )
                    with gr.Row():
                        _styles_choices = get_style_choices()
                        dd_styles_gen = gr.Dropdown(
                            label="Styles",
                            choices=_styles_choices,
                            multiselect=True,
                            value=[s for s in gen_config.get("active_styles", []) if s in _styles_choices],
                            scale=1,
                            info="Apply art styles or lighting presets."
                        )
                        btn_refresh_styles_gen = gr.Button("🔄", scale=0, min_width=40)
                    
                    # --- GENERATION MODE SELECTION ---
                    gr.Markdown("### 🎛️ Generation Mode")
                    radio_gen_mode = gr.Radio(
                        choices=["txt2img", "img2img", "controlnet"],
                        value=gen_config.get("generation_mode", "txt2img"),
                        label="Mode",
                        info="txt2img: Text only | img2img: Template image | ControlNet: OpenPose",
                        interactive=True
                    )
                    
                    # Img2Img Panel
                    with gr.Column(visible=(gen_config.get("generation_mode") == "img2img")) as panel_img2img:
                        gr.Markdown("#### 🖼️ Img2Img Settings")
                        img_template = gr.Image(
                            label="Template Image", 
                            value=gen_config.get("img2img_template") or None,
                            type="filepath", 
                            interactive=True,
                            height=150
                        )
                        with gr.Row():
                            slider_denoising = gr.Slider(
                                label="Denoising Strength", 
                                minimum=0, maximum=1, value=gen_config.get("img2img_denoising", 0.75), step=0.05,
                                info="Higher = more change from template"
                            )
                            chk_ignore_height = gr.Checkbox(
                                label="Ignore Height Guide", 
                                value=gen_config.get("img2img_ignore_height_guide", False),
                                info="Don't stretch template for character heights"
                            )
                        txt_img2img_warning = gr.Markdown("", visible=False)
                    
                    # ControlNet Panel
                    with gr.Column(visible=(gen_config.get("generation_mode") == "controlnet")) as panel_controlnet:
                        gr.Markdown("#### 🎮 ControlNet (OpenPose)")
                        img_pose = gr.Image(
                            label="Pose Image", 
                            value=gen_config.get("controlnet_pose") or None,
                            type="filepath", 
                            interactive=True,
                            height=150
                        )
                        with gr.Row():
                            dd_cn_module = gr.Dropdown(
                                label="Preprocessor", 
                                choices=["dw_openpose_full", "openpose", "openpose_face", "openpose_hand", "openpose_full", "none"],
                                value=gen_config.get("controlnet_module", "dw_openpose_full"),
                                scale=1
                            )
                            dd_cn_model = gr.Dropdown(
                                label="ControlNet Model", 
                                choices=[],  # Populated on refresh
                                value=gen_config.get("controlnet_model"),
                                allow_custom_value=True,
                                scale=2,
                                info="Click 🔄 to load models from Forge"
                            )
                            btn_refresh_cn = gr.Button("🔄", scale=0, min_width=40)
                        
                        with gr.Row():
                            chk_cn_pixel_perfect = gr.Checkbox(
                                label="Pixel Perfect", 
                                value=gen_config.get("controlnet_pixel_perfect", True),
                                info="Auto-calculate resolution"
                            )
                            num_cn_res = gr.Number(
                                label="Preprocessor Resolution", 
                                value=gen_config.get("controlnet_processor_res", 512), 
                                precision=0,
                                interactive=not gen_config.get("controlnet_pixel_perfect", True),
                                info="Resolution (if Pixel Perfect off)"
                            )



                        with gr.Row():
                            slider_cn_start = gr.Slider(
                                label="Guidance Start",
                                minimum=0.0, maximum=1.0, step=0.01,
                                value=gen_config.get("controlnet_guidance_start", 0.0),
                                info="Start (0-1)"
                            )
                            slider_cn_end = gr.Slider(
                                label="Guidance End",
                                minimum=0.0, maximum=1.0, step=0.01,
                                value=gen_config.get("controlnet_guidance_end", 1.0),
                                info="End (0-1)"
                            )

                        slider_cn_weight = gr.Slider(
                            label="ControlNet Weight", 
                            minimum=0, maximum=2, value=gen_config.get("controlnet_weight", 1.0), step=0.1,
                            info="Influence of the pose control"
                        )
                        dd_cn_control_mode = gr.Dropdown(
                            label="Control Mode",
                            choices=["Balanced", "My prompt is more important", "ControlNet is more important"],
                            value=gen_config.get("controlnet_control_mode", "ControlNet is more important"),
                            info="Priority between prompt and ControlNet"
                        )
                    
                    txt_active_main = gr.Textbox(label="Active Characters", value=get_active_summary(), interactive=False)
                    with gr.Row():
                        btn_gen_chars_main = gr.Button("🚀 GENERATE ALL CHARACTERS", variant="primary", interactive=False, scale=3)
                        btn_cancel_gen = gr.Button("🛑 Cancel & Delete", variant="stop", scale=1)

                    
                    
                with gr.Column(scale=1):
                    preview = gr.Image(label="Preview", value=get_latest_set_preview(), interactive=False, height="auto")
            
            with gr.Row():
                gr.Column(scale=1)
                with gr.Column(scale=2):
                    status_box = gr.Textbox(label="Status", interactive=False)
                    with gr.Row():
                        forge_status = gr.Textbox(label="Forge Status", interactive=False, value="🔴 OFFLINE", scale=3)
                        with gr.Column(scale=1, min_width=120):
                            btn_refresh = gr.Button("🔄", min_width=50)
                            btn_quick_launch = gr.Button("🚀 Launch", variant="primary", visible=True)
                gr.Column(scale=1)
        
        with gr.Tab("Set Editor"):
            with gr.Row():
                with gr.Column(scale=4):
                    with gr.Row():
                        dd_sets = gr.Dropdown(label="Select Set", choices=list_sets(), scale=3)
                        btn_refresh_sets = gr.Button("🔄", scale=0, min_width=40)
                        btn_rename_set = gr.Button("✏️", scale=0, min_width=40)
                    
                    with gr.Row(visible=False) as row_rename_set:
                         txt_rename_set = gr.Textbox(label="New Name", scale=3)
                         btn_confirm_rename = gr.Button("✅ Rename", variant="primary", scale=1)
                         btn_cancel_rename = gr.Button("❌ Cancel", scale=0)

                    with gr.Row():
                        display_mode = gr.Radio(["Frieze", "Grid"], label="Display Mode", value="Frieze", scale=1, info="Frieze: Side-by-side | Grid: Standard overview.")
                        zoom_slider = gr.Slider(label="Zoom", minimum=100, maximum=1000, value=400, step=50, scale=2, info="Adjust preview size.")
                
                with gr.Column(scale=3):
                    with gr.Group():
                        gr.Markdown("**🧩 Merge Tool**")
                        with gr.Row():
                            slider_merge_overlap = gr.Slider(label="Overlap", minimum=-100, maximum=100, value=0, step=10, info="Horizontal spacing between images.")
                            btn_merge = gr.Button("Merge Images", variant="secondary")
                        gr.Markdown("**✂️ BG Removal**")
                        with gr.Row():
                            slider_bg_threshold = gr.Slider(label="Threshold", minimum=0, maximum=200, value=20, step=1, info="Higher = more aggressive removal.")
                            cb_bg_contiguous = gr.Checkbox(label="Contiguous", value=True, info="Edge-only removal.")
                        with gr.Row():
                            btn_remove_bg = gr.Button("Remove BG", size="sm")
                            btn_restore_bg = gr.Button("Restore BG", size="sm")

            with gr.Row():
                btn_send_to_gen = gr.Button("♻️ Send to Generation", variant="primary", scale=2)
                btn_delete_set = gr.Button("🗑️ Delete Set", variant="stop", scale=1)
                export_file = gr.File(label="Export File", visible=False, scale=1)
                
            merge_status = gr.Textbox(label="Status", interactive=False, scale=3)
            
            with gr.Row(visible=False) as row_delete_set_confirm:
                gr.Markdown("⚠️ **Are you sure you want to delete this set?** This will delete ALL images in the set.")
                btn_confirm_delete_set = gr.Button("🔥 YES, DELETE", variant="stop", scale=1)
                btn_cancel_delete_set = gr.Button("❌ Cancel", scale=1)
            
            refresh_trigger = gr.State(0)
            

            btn_remove_bg.click(
                fn=remove_background_from_set,
                inputs=[dd_sets, slider_bg_threshold, cb_bg_contiguous],
                outputs=[gr.Number(visible=False), merge_status]
            ).then(
                fn=lambda s: s, # Just trigger re-render
                inputs=[dd_sets],
                outputs=[dd_sets] # Hacky way to trigger render update via change? Not really.
            ).then(
                 fn=lambda: gr.update(value=time.time()), # Trigger re-render via state
                 outputs=[refresh_trigger]
            ).then(inc_trigger, inputs=[refresh_trigger], outputs=[refresh_trigger])

            btn_restore_bg.click(
                fn=restore_background_from_set,
                inputs=[dd_sets],
                outputs=[gr.Number(visible=False), merge_status]
            ).then(inc_trigger, inputs=[refresh_trigger], outputs=[refresh_trigger])
            
            btn_delete_set.click(fn=lambda: gr.update(visible=True), outputs=[row_delete_set_confirm])
            btn_cancel_delete_set.click(fn=lambda: gr.update(visible=False), outputs=[row_delete_set_confirm])
            
            def do_delete_set(set_name):
                if not set_name: return gr.update(visible=False), gr.update(), "❌ No set selected"
                delete_set(set_name)
                sets = list_sets()
                return gr.update(visible=False), gr.update(choices=sets, value=sets[0] if sets else None), f"🗑️ Set '{set_name}' deleted"
            
            btn_confirm_delete_set.click(
                fn=do_delete_set,
                inputs=[dd_sets],
                outputs=[row_delete_set_confirm, dd_sets, merge_status]
            )

            # --- Rename Set Logic ---
            btn_rename_set.click(
                fn=lambda s: (gr.update(visible=True), s),
                inputs=[dd_sets],
                outputs=[row_rename_set, txt_rename_set]
            )
            
            btn_cancel_rename.click(
                fn=lambda: gr.update(visible=False),
                outputs=[row_rename_set]
            )
            
            def do_rename_set_action(old_name, new_name):
                if not old_name: return gr.update(), gr.update(), "❌ No set selected"
                success, msg = rename_set(old_name, new_name)
                if not success:
                    return gr.update(), gr.update(), msg
                
                # Refresh sets
                sets = list_sets()
                return gr.update(visible=False), gr.update(choices=sets, value=new_name), msg
            
            btn_confirm_rename.click(
                fn=do_rename_set_action,
                inputs=[dd_sets, txt_rename_set],
                outputs=[row_rename_set, dd_sets, merge_status]
            ).then(inc_trigger, inputs=[refresh_trigger], outputs=[refresh_trigger])

            # --- Nudge Panel (Static) ---
            nudge_target_index = gr.State(-1)
            with gr.Group(visible=False) as nudge_panel:
                with gr.Row():
                    gr.Markdown("### 🎨 Custom Nudge")
                    btn_close_nudge = gr.Button("❌", size="sm", scale=0)
                with gr.Row():
                    txt_nudge_prompt = gr.Textbox(label="Extra Prompt (High Priority)", placeholder="e.g. smile", scale=3)
                    txt_nudge_negative = gr.Textbox(label="Extra Negative", placeholder="e.g. bad hands", scale=3)
                with gr.Row():
                    with gr.Column(scale=1):
                        img_nudge_source = gr.Image(label="Source Image", type="pil", height=200)
                        btn_use_current = gr.Button("⬇️ Use Current Image")
                    with gr.Column(scale=2):
                        slider_nudge_strength = gr.Slider(
                            label="Denoising / Control Weight", 
                            minimum=0, maximum=1, value=0.75, step=0.05,
                            info="0 = original image (no change), 1 = completely new image"
                        )
                        btn_exec_nudge = gr.Button("⚡ Regenerate", variant="primary")

            def open_nudge_ui(idx): return gr.update(visible=True), idx, "", "", None
            btn_close_nudge.click(lambda: gr.update(visible=False), outputs=[nudge_panel])
            
            def use_current_image(idx, s_name):
                if idx < 0: return None
                s_data = load_set(s_name)
                if not s_data: return None
                fname = s_data["images"][idx]["filename"]
                path = os.path.join(get_set_path(s_name), fname)
                return Image.open(path) if os.path.exists(path) else None
                
            btn_use_current.click(fn=use_current_image, inputs=[nudge_target_index, dd_sets], outputs=[img_nudge_source])

            def do_nudge(s_name, idx, p, n, s, strength):
                 if idx < 0: return "❌ No target selected"
                 params = {"prompt": p, "negative": n, "source_image": s, "strength": strength}
                 gen = regenerate_set_image(s_name, idx, params)
                 msg = ""
                 for res in gen:
                     if isinstance(res, tuple): msg = res[1]
                     else: msg = res
                 return msg

            btn_exec_nudge.click(
                fn=do_nudge,
                inputs=[dd_sets, nudge_target_index, txt_nudge_prompt, txt_nudge_negative, img_nudge_source, slider_nudge_strength],
                outputs=[status_box]
            ).then(inc_trigger, inputs=[refresh_trigger], outputs=[refresh_trigger])

            # --- A/B Test Panel ---
            ab_target_index = gr.State(-1)
            ab_variant_path = gr.State(None)
            
            with gr.Group(visible=False) as ab_panel:
                with gr.Row():
                    gr.Markdown("### ⚖️ A/B Comparison")
                    btn_close_ab = gr.Button("❌", size="sm", scale=0)
                
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("#### Option A (Current)")
                        img_ab_a = gr.Image(label="Original", interactive=False, height=600)
                        btn_keep_a_stop = gr.Button("⏹️ Keep A & Stop")
                        btn_keep_a_retry = gr.Button("🎲 Keep A & Retry B")
                    
                    with gr.Column():
                        gr.Markdown("#### Option B (Variant)")
                        img_ab_b = gr.Image(label="Variant", interactive=False, height=600)
                        btn_keep_b_retry = gr.Button("✅ Keep B & Iterate (B becomes A)")
                
                with gr.Row():
                     slider_ab_similarity = gr.Slider(
                         label="Similarity % (Higher = closer to original)", 
                         minimum=0.0, maximum=1.0, value=0.9, step=0.05
                     )
                     status_ab = gr.Textbox(label="Status", interactive=False)

            def close_ab():
                return gr.update(visible=False), -1, None
            
            btn_close_ab.click(fn=close_ab, outputs=[ab_panel, ab_target_index, ab_variant_path])
            btn_keep_a_stop.click(fn=close_ab, outputs=[ab_panel, ab_target_index, ab_variant_path])

            def start_ab_test(set_name, idx):
                if idx < 0: return gr.update(), gr.update(), None, "❌ Invalid Index"
                
                s_data = load_set(set_name)
                if not s_data: return gr.update(), gr.update(), None, "❌ Set not found"
                
                fname = s_data["images"][idx]["filename"]
                path = os.path.join(get_set_path(set_name), fname)
                
                if not os.path.exists(path): return gr.update(), gr.update(), None, "❌ Image missing"
                
                # Load A
                img_a = Image.open(path)
                
                # Clear B
                return gr.update(visible=True), idx, img_a, None, "Ready. Generating B..."

            def run_ab_generation(set_name, idx, similarity):
                if idx < 0: return None, "❌ No selection", None
                
                gen = generate_variant(set_name, idx, similarity)
                img_path = None
                msg = ""
                for res in gen:
                    if isinstance(res, tuple): 
                         img_path = res[0]
                         msg = res[1]
                    else: 
                         msg = res
                
                return img_path, msg, img_path
            
            def on_keep_b_retry(set_name, idx, variant_path, similarity):
                if not variant_path or not os.path.exists(variant_path):
                    return gr.update(), gr.update(), None, "❌ No variant to keep"
                
                # 1. Read metadata from variant to get params
                # Note: We need to parse PngInfo 'parameters' text back to dict if possible?
                # Or we can just re-use the OLD params but update the seed?
                # Actually, main parameters (prompt etc) are same as origin.
                # Only difference is it's an img2img result now.
                # But to properly support "Save Parameters", we should try to get them.
                # Since parsing "parameters" text is hard without library, 
                # we will trust that `generation.py` saved a good image.
                # Use `add_image_to_set` logic which is safer than `replace_image_in_set`.
                
                s_data = load_set(set_name)
                if not s_data: return gr.update(), gr.update(), None, "❌ Set missing"
                
                old_img = s_data["images"][idx]
                char_name = old_img["char_name"]
                
                # Reuse old params but update prompt if we had changed it (we didn't yet support prompt editing in AB)
                # Ideally we want to store the "denoising strength" and "seed" used.
                params = old_img.get("params", {}).copy()
                params["_generation_mode"] = "img2img" 
                # We don't easily know the new seed unless we parse it.
                # But it's better than nothing.
                
                # Move variant to set folder properly
                target_path, clean_filename = prepare_set_image_path(set_name, char_name)
                shutil.copy(variant_path, target_path) 
                
                # Update set data
                add_image_to_set(set_name, clean_filename, char_name, params)
                
                # 2. Reload valid A (the new one)
                new_a_path = target_path
                new_a = Image.open(new_a_path)
                
                # 3. Generate new B (return None for B initially)
                return new_a, None, None, "✅ B Promoted! Generating new variant..."

            # Event Wiring
            btn_keep_b_retry.click(
                fn=on_keep_b_retry,
                inputs=[dd_sets, ab_target_index, ab_variant_path, slider_ab_similarity],
                outputs=[img_ab_a, img_ab_b, ab_variant_path, status_ab]
            ).then(
                fn=run_ab_generation,
                inputs=[dd_sets, ab_target_index, slider_ab_similarity],
                outputs=[img_ab_b, status_ab, ab_variant_path] 
            ).then(inc_trigger, inputs=[refresh_trigger], outputs=[refresh_trigger])
            
            btn_keep_a_retry.click(
                fn=run_ab_generation,
                inputs=[dd_sets, ab_target_index, slider_ab_similarity],
                outputs=[img_ab_b, status_ab, ab_variant_path]
            )
            

            # Pixel Perfect Toggle Logic
            chk_cn_pixel_perfect.change(
                fn=lambda x: gr.update(interactive=not x),
                inputs=[chk_cn_pixel_perfect],
                outputs=[num_cn_res]
            )

            @gr.render(inputs=[dd_sets, display_mode, zoom_slider, refresh_trigger])
            def render_set(set_name, mode, zoom, trigger):
                if not set_name: return
                set_data = load_set(set_name)
                if not set_data:
                    gr.Markdown("❌ Failed to load set.")
                    return
                images = set_data.get("images", [])
                if not images:
                    gr.Markdown("📁 Set is empty.")
                    return
                    
                if mode == "Frieze":
                    forge_online = find_forge()[0]
                    with gr.Row(variant="panel", elem_id="frieze_container"):
                        for i, img in enumerate(images):
                            with gr.Column(min_width=zoom, scale=0, elem_classes=["frieze_column"]):
                                img_path = os.path.join(get_set_path(set_name), img["filename"])
                                gr.Image(img_path, label=img["char_name"], show_label=False, interactive=False, container=False, width=zoom)
                                
                                # Row 1: Order & File
                                with gr.Row(elem_classes=["frieze_button_row"]):
                                    btn_left = gr.Button("⬅️", size="sm", interactive=(i > 0))
                                    btn_right = gr.Button("➡️", size="sm", interactive=(i < len(images) - 1))
                                    btn_flip = gr.Button("↔️", size="sm")
                                    btn_rep = gr.UploadButton("📂", size="sm", file_types=["image"])

                                # Row 2: Tools & Save
                                with gr.Row(elem_classes=["frieze_button_row"]):
                                    btn_refresh = gr.Button("🔄", size="sm", interactive=forge_online)
                                    btn_nudge = gr.Button("🪄", size="sm", interactive=forge_online)
                                    btn_ab = gr.Button("⚖️", size="sm", interactive=forge_online)
                                    btn_save = gr.Button("💾", size="sm")

                                # Stable handlers using closures
                                def make_handler(func, *args):
                                    def handler(t):
                                        func(*args)
                                        return t + 1
                                    return handler

                                btn_left.click(fn=make_handler(move_image_left, set_name, i), inputs=[refresh_trigger], outputs=[refresh_trigger])
                                btn_right.click(fn=make_handler(move_image_right, set_name, i), inputs=[refresh_trigger], outputs=[refresh_trigger])
                                
                                def flip_handler(t):
                                    msg = flip_image_wrapper(set_name, i)
                                    return t + 1, msg
                                btn_flip.click(fn=flip_handler, inputs=[refresh_trigger], outputs=[refresh_trigger, status_box])
                                
                                def refresh_img_handler(t):
                                    # regenerate_set_image is a generator, we need to consume it
                                    gen = regenerate_set_image(set_name, i)
                                    msg = ""
                                    for res in gen:
                                        if isinstance(res, tuple): msg = res[1]
                                        else: msg = res
                                    return t + 1, msg
                                btn_refresh.click(fn=refresh_img_handler, inputs=[refresh_trigger], outputs=[refresh_trigger, status_box])
                                
                                def open_nudge_handler():
                                    return open_nudge_ui(i)
                                btn_nudge.click(fn=open_nudge_handler, outputs=[nudge_panel, nudge_target_index, txt_nudge_prompt, txt_nudge_negative, img_nudge_source])
                                
                                def start_ab_handler():
                                    return start_ab_test(set_name, i)
                                
                                def run_ab_handler(similarity):
                                    return run_ab_generation(set_name, i, similarity)

                                btn_ab.click(
                                    fn=start_ab_handler, 
                                    outputs=[ab_panel, ab_target_index, img_ab_a, img_ab_b, status_ab]
                                ).then(
                                    fn=run_ab_handler,
                                    inputs=[slider_ab_similarity],
                                    outputs=[img_ab_b, status_ab, ab_variant_path]
                                )
                                
                                def upload_handler(file_obj, t):
                                    replace_image_wrapper(set_name, i, file_obj)
                                    return t + 1
                                btn_rep.upload(fn=upload_handler, inputs=[btn_rep, refresh_trigger], outputs=[refresh_trigger])
                                
                                btn_save.click(fn=lambda p=img_path: gr.update(value=p, visible=True), outputs=[export_file])
                else:
                    with gr.Row(variant="panel"):
                         gr.Gallery([os.path.join(get_set_path(set_name), img["filename"]) for img in images], columns=4)

                    
        with gr.Tab("Characters"):
            gr.Markdown("### 👥 Character Editor")
            
            with gr.Row():
                dd_character = gr.Dropdown(
                    label="Select Character",
                    choices=get_character_files(),
                    value=None,
                    allow_custom_value=False,
                    scale=3,
                    info="Choose a character to edit."
                )
                btn_refresh_chars = gr.Button("🔄", scale=0, min_width=50)
                btn_save_char_top = gr.Button("💾 Save", variant="primary", scale=1)
                txt_rename_char = gr.Textbox(label="Rename Current", placeholder="New name here...", scale=2, info="Change the file name.")
                btn_rename_char = gr.Button("✏️ Rename", variant="secondary", scale=1)
                txt_new_char_name = gr.Textbox(label="Create New", placeholder="Character name", scale=2, info="Start a fresh profile.")
                dd_new_char_cat = gr.Dropdown(label="Category", choices=MODEL_CATEGORIES, value="Illustrious", scale=1, info="Base model target.")
                btn_new_char = gr.Button("➕ Create", variant="primary", scale=1)
            
            with gr.Row():
                with gr.Column(scale=1):
                    with gr.Row():
                        txt_add_outfit = gr.Textbox(label="Add Custom Outfit (key: Name)", placeholder="maid: Maid Outfit", scale=3, info="e.g. 'maid: Maid Outfit'")
                        btn_add_outfit = gr.Button("👗 Add", scale=1)
                with gr.Column(scale=1):
                    with gr.Row():
                        txt_add_morph = gr.Textbox(label="Add Custom Morph (key: Name)", placeholder="cat: Cat Ears", scale=3, info="e.g. 'cat: Cat Ears'")
                        btn_add_morph = gr.Button("🧬 Add", scale=1)
                with gr.Column(scale=1):
                    with gr.Row():
                        txt_add_body = gr.Textbox(label="Add Custom Body Part (key: Name)", placeholder="nails: Long Nails", scale=3, info="e.g. 'nails: Nails'")
                        btn_add_body = gr.Button("👤 Add", scale=1)
            
            gr.Markdown("### Base Prompts")
            with gr.Row():
                txt_char_positive = gr.Textbox(label="Positive Prompt", lines=2, placeholder="1girl,...", scale=3, info="Physical traits (hair, eyes, face).")
                txt_char_negative = gr.Textbox(label="Negative Prompt", lines=2, placeholder="...", scale=3, info="Character-specific negatives.")
            
            txt_char_loras = gr.Textbox(label="LoRA References (Names / URLs) - [Reference Only]", lines=3, placeholder="<lora:Name:1>, http://civitai.com/...", info="For your records (doesn't affect prompt).")
            
            with gr.Row():
                dd_height_guide = gr.Dropdown(
                    label="Height Guide (experimental)",
                    choices=[v["label"] for v in HEIGHT_GUIDES.values()],
                    value="Average",
                    info="Stretches template/pose to create height variation in lineups",
                    scale=1
                )
                dd_char_model_category = gr.Dropdown(
                    label="Model Category",
                    choices=MODEL_CATEGORIES,
                    value="Illustrious",
                    scale=1
                )
            gr.Markdown("*Height Guide affects img2img and ControlNet modes only*")
            
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### 👤 Body")

                    body_inputs = []
                    body_suggestion_btns = {}
                    
                    # Optimization: Fetch config and keys once
                    gen_cfg = load_gen_config()
                    show_suggestions = should_show_suggestions()
                    body_names = gen_cfg.get("body_names", DEFAULT_GEN_CONFIG["body_names"])
                    body_keys = list(body_names.keys())
                    
                    body_accs = []
                    for key in body_keys:
                        display_name = body_names.get(key, key)
                        acc = gr.Accordion(display_name, open=False)
                        with acc:
                            with gr.Group():
                                if key == "penis":
                                    with gr.Row(visible=True) as row_futa_warn:
                                        gr.Markdown("> ⚠️ Futa features should be handled in Morphs. Use Penis only if the character base is endowed with one.")
                                        btn_futa_warn_ok = gr.Button("OK", scale=1, size="sm")
                                        btn_futa_warn_ok.click(fn=lambda: gr.update(visible=False), outputs=[row_futa_warn])

                                pos_input = gr.Textbox(label="Positive", placeholder="body part tags...", lines=1)
                                neg_input = gr.Textbox(label="Negative", placeholder="body part negative tags...", lines=1)
                                suggestions = get_suggestions_for_key(key)
                                if suggestions and show_suggestions:
                                    with gr.Row(elem_classes=["tag-row"]):
                                        for tag in suggestions[:10]:
                                            btn = gr.Button(tag, size="sm", min_width=60)
                                            body_suggestion_btns[(key, tag)] = (btn, pos_input)
                                body_inputs.extend([pos_input, neg_input])
                        body_accs.append(acc)

                with gr.Column():
                    gr.Markdown("### 👗 Outfits")
                    outfit_inputs = []
                    outfit_suggestion_btns = {}
                    
                    outfit_names = gen_cfg.get("outfit_names", DEFAULT_GEN_CONFIG["outfit_names"])
                    outfit_keys = list(outfit_names.keys())
                    
                    outfit_accs = []
                    for key in outfit_keys:
                        display_name = outfit_names.get(key, key)
                        acc = gr.Accordion(display_name, open=False)
                        with acc:
                            with gr.Group():
                                pos_input = gr.Textbox(label="Positive", placeholder="outfit tags to add...", lines=1)
                                neg_input = gr.Textbox(label="Negative", placeholder="outfit negative tags...", lines=1)
                                suggestions = get_suggestions_for_key(key)
                                if suggestions and show_suggestions:
                                    with gr.Row(elem_classes=["tag-row"]):
                                        for tag in suggestions[:10]:
                                            btn = gr.Button(tag, size="sm", min_width=60)
                                            outfit_suggestion_btns[(key, tag)] = (btn, pos_input)
                                outfit_inputs.extend([pos_input, neg_input])
                        outfit_accs.append(acc)
                
                with gr.Column():
                    gr.Markdown("### 🧬 Morphs")
                    morph_inputs = []
                    morph_suggestion_btns = {}
                    
                    morph_names = gen_cfg.get("morph_names", DEFAULT_GEN_CONFIG["morph_names"])
                    morph_keys = list(morph_names.keys())
                    
                    morph_accs = []
                    for key in morph_keys:
                        display_name = morph_names.get(key, key)
                        acc = gr.Accordion(display_name, open=False)
                        with acc:
                            with gr.Group():
                                pos_input = gr.Textbox(label="Positive", placeholder="morph tags to add...", lines=1)
                                neg_input = gr.Textbox(label="Negative", placeholder="morph negative tags...", lines=1)
                                suggestions = get_suggestions_for_key(key)
                                if suggestions and show_suggestions:
                                    with gr.Row(elem_classes=["tag-row"]):
                                        for tag in suggestions[:10]:
                                            btn = gr.Button(tag, size="sm", min_width=60)
                                            morph_suggestion_btns[(key, tag)] = (btn, pos_input)
                                morph_inputs.extend([pos_input, neg_input])
                        morph_accs.append(acc)
            
            with gr.Row():
                btn_save_char = gr.Button("💾 Save Character", variant="primary")
                btn_delete_char = gr.Button("🗑️ Delete", variant="stop")
            
            with gr.Row(visible=False) as row_delete_confirm:
                gr.Markdown("⚠️ **Are you sure you want to delete this character?** This cannot be undone.")
                btn_confirm_delete = gr.Button("🔥 YES, DELETE", variant="stop", scale=1)
                btn_cancel_delete = gr.Button("❌ Cancel", scale=1)
            
            char_status = gr.Textbox(label="Status", interactive=False)

        with gr.Tab("Styles"):
            gr.Markdown("### 🎨 Style Editor")
            with gr.Row():
                dd_style = gr.Dropdown(
                    label="Select Style",
                    choices=get_style_files(),
                    value=None,
                    allow_custom_value=False,
                    scale=3,
                    info="Choose a style preset to edit."
                )
                btn_refresh_styles = gr.Button("🔄", scale=0, min_width=50)
                btn_save_style_top = gr.Button("💾 Save", variant="primary", scale=1)
                txt_new_style_name = gr.Textbox(label="Create New Style", placeholder="Style Name", scale=2, info="New style preset.")
                dd_new_style_cat = gr.Dropdown(label="Category", choices=MODEL_CATEGORIES, value="Illustrious", scale=1, info="Target model.")
                btn_new_style = gr.Button("➕ Create", variant="primary", scale=1)
            
            with gr.Row():
                txt_style_name = gr.Textbox(label="Style Name", placeholder="Display Name", scale=2)
                dd_style_model_category = gr.Dropdown(label="Model Category", choices=MODEL_CATEGORIES, value="Illustrious", scale=1)
                btn_save_style = gr.Button("💾 Save Changes", variant="primary", scale=1)
                btn_delete_style = gr.Button("🗑️ Delete", variant="stop", scale=1)
            
            with gr.Row():
                txt_style_positive = gr.Textbox(label="Positive Prompt", lines=3, placeholder="art style, lighting, etc.", info="Aesthetic, artist, lighting tags.")
                txt_style_negative = gr.Textbox(label="Negative Prompt", lines=3, placeholder="...", info="Tags to avoid for this style.")
            
            txt_style_loras = gr.TextArea(label="LoRA References (Names / URLs) - [Reference Only]", lines=3, placeholder="name:weight or <lora:name:weight>")
            
            style_status = gr.Textbox(label="Status", interactive=False)

        with gr.Tab("Active Characters"):
            gr.Markdown("### 👥 Active Characters & Presets")
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("#### 📋 Presets")
                    dd_preset = gr.Dropdown(
                        label="Load Preset",
                        choices=get_preset_files(),  # Only user-saved presets here, not generated ones
                        allow_custom_value=False,
                        info="Load a previously saved character queue."
                    )
                    btn_load_preset = gr.Button("📂 Load Preset", variant="primary")
                    
                    with gr.Row():
                        btn_activate_all = gr.Button("✅ Activate All", variant="secondary")
                        btn_deactivate_all = gr.Button("❌ Deactivate All", variant="secondary")
                    
                    with gr.Row():
                        txt_preset_name = gr.Textbox(label="Preset Name", placeholder="pokemon_girls", scale=2, info="Name for the current queue.")
                        btn_save_preset = gr.Button("💾 Save", variant="secondary")
                        btn_delete_preset = gr.Button("🗑️ Delete Preset", variant="stop")
                    
                    with gr.Row():
                         btn_new_empty_preset = gr.Button("🆕 New Empty Preset", size="sm")
                         btn_new_full_preset = gr.Button("🆕 New Full Preset", size="sm")

                    preset_status = gr.Textbox(label="Status", interactive=False)
                
                with gr.Column(scale=2):
                    gr.Markdown("#### 📝 Active Queue (Order Matters)")
                    # This textbox is the Source of Truth for generation order
                    # Restore session queue if available
                    _session_names = gen_config.get("active_character_names", [])
                    if _session_names:
                         set_active_characters_from_list(_session_names)
                         
                    txt_active_order = gr.TextArea(
                        label="Character Order (One per line or comma separated)", 
                        # Init with saved list or current active
                        value="\n".join(_session_names) if _session_names else "\n".join([c["name"] for c in get_active_characters()]),
                        interactive=True, 
                        lines=10,
                        placeholder="Alice\nBob\nCharlie",
                        info="Final generation queue. Order matters!"
                    )
                    
                    gr.Markdown("#### 🔳 Quick Select")
                    all_chars = get_character_files()
                    active_chars = get_active_characters()
                    active_names = [c["name"] for c in active_chars]
                    
                    cbg_active_chars = gr.CheckboxGroup(
                        label="Available Characters",
                        choices=all_chars,
                        value=active_names,
                        interactive=True
                    )

        with gr.Tab("Settings"):
            gr.Markdown("### ⚙️ Settings")
            
            with gr.Tabs():
                with gr.Tab("Generation Settings"):
                    with gr.Row():
                        dd_model = gr.Dropdown(label="Model", choices=get_models_list(), value=gen_config["model"], allow_custom_value=True)
                        dd_vae = gr.Dropdown(label="VAE", choices=get_vae_list(), value=gen_config["vae"], allow_custom_value=True)
                        dd_sampler = gr.Dropdown(label="Sampler", choices=get_samplers_list(), value=gen_config["sampler"], allow_custom_value=True)
                        btn_refresh_lists = gr.Button("🔄 Refresh", scale=0)
                    
                    with gr.Row():
                        slider_cfg = gr.Slider(label="CFG Scale", minimum=1, maximum=20, value=gen_config["cfg_scale"], step=0.5, info="Lower = more creative | Higher = closer to prompt")
                        slider_steps = gr.Slider(label="Steps", minimum=1, maximum=100, value=gen_config["steps"], step=1, info="Refinement iterations.")
                    
                    gr.Markdown("### 📐 Image Size (SDXL optimized)")
                    with gr.Row():
                        dd_size = gr.Dropdown(
                            label="Preset Size", 
                            choices=[f"{w}x{h}" for w, h in SDXL_SIZES],
                            value=f"{gen_config['width']}x{gen_config['height']}"
                        )
                        num_width = gr.Number(label="Width", value=gen_config["width"], precision=0)
                        num_height = gr.Number(label="Height", value=gen_config["height"], precision=0)
                    
                    gr.Markdown("### 📝 Common Prompts")
                    txt_common_prompt = gr.Textbox(label="Common Prompt", value=gen_config["common_prompt"], lines=2, info="Global quality tags added to ALL images.")
                    txt_common_neg = gr.Textbox(label="Common Negative", value=gen_config["common_negative"], lines=2, info="Global negatives (worst quality, etc.)")
                    
                    gr.Markdown("### 🏷️ Tag Suggestions")
                    chk_show_suggestions = gr.Checkbox(
                        label="Show tag suggestions in Character Editor (requires page refresh)",
                        value=gen_config.get("show_suggestions", True)
                    )
                    chk_save_metadata = gr.Checkbox(
                        label="Save Generation Metadata in Images", 
                        value=config.get("save_metadata", True)
                    )
                    
                    gr.Markdown("### 🖼️ Merge Output")
                    dd_merge_format = gr.Dropdown(
                        label="Merge Format",
                        choices=["png", "webp"],
                        value=gen_config.get("merge_format", "webp"),
                        info="WebP is much smaller, PNG is more compatible."
                    )

                with gr.Tab("Global Lists"):
                    gr.Markdown("Modify the key: name mappings. One per line.")
                    txt_manage_outfits = gr.Textbox(label="Outfits", value=get_outfit_names_text(), lines=10)
                    txt_manage_morphs = gr.Textbox(label="Morphs", value=get_morph_names_text(), lines=10)
                    txt_manage_body = gr.Textbox(label="Body", value=get_body_names_text(), lines=10)
            
            with gr.Row():
                btn_save_settings = gr.Button("💾 Save All Settings", variant="primary")
                settings_status = gr.Textbox(label="Status", interactive=False, scale=2)
        
        with gr.Tab("Forge Server"):
            gr.Markdown("### 🎛️ Forge Server Control")
            
            with gr.Row():
                forge_status_server = gr.Textbox(label="Forge Status", interactive=False, value="🔴 OFFLINE", scale=3)
                btn_refresh_server = gr.Button("🔄", scale=0, min_width=50)
            
            txt_api_url = gr.Textbox(
                label="API URL (will also scan common ports)",
                value=config["api_url"],
                placeholder="http://127.0.0.1:7860"
            )
            
            txt_forge_path = gr.Textbox(
                label="Path to launcher (webui.sh on Linux, webui-user.bat on Windows)",
                value=config["forge_path"],
                placeholder="/path/to/webui.sh or C:\\path\\to\\webui-user.bat"
            )
            
            txt_extra_args = gr.Textbox(
                label="Additional arguments",
                value=config["extra_args"],
                placeholder="--api --listen --nowebui",
                info="CLI flags passed to Forge on launch."
            )

            
            gr.Markdown("""
            **Headless Mode:** Default args `--api --listen --nowebui` launch Forge without its Web UI (saves VRAM).  
            Only the API will be available for this tool.
            """)
            
            with gr.Row():
                btn_launch = gr.Button("🚀 LAUNCH FORGE", variant="primary")
                btn_kill = gr.Button("💀 KILL ALL FORGE", variant="stop")
                btn_save = gr.Button("💾 Save Settings", variant="secondary")
            
            server_status = gr.Textbox(label="Server Status", interactive=False)

    # --- Actions ---
    
    # Status refresh
    btn_refresh.click(
        fn=refresh_status,
        outputs=[forge_status, forge_status_server, btn_launch, btn_quick_launch, btn_gen_chars_main, dd_outfits_main, dd_morphs_main, dd_body_main, dd_cn_module]
    )
    
    btn_refresh_server.click(
        fn=refresh_status,
        outputs=[forge_status, forge_status_server, btn_launch, btn_quick_launch, btn_gen_chars_main, dd_outfits_main, dd_morphs_main, dd_body_main, dd_cn_module]
    )
    
    # Quick launch from main screen
    btn_quick_launch.click(
        fn=launch_forge,
        inputs=[txt_forge_path, txt_extra_args],
        outputs=[status_box]
    ).then(
        fn=refresh_status,
        outputs=[forge_status, forge_status_server, btn_launch, btn_quick_launch, btn_gen_chars_main, dd_outfits_main, dd_morphs_main, dd_body_main, dd_cn_module]
    ).then(
        fn=refresh_dropdowns,
        outputs=[dd_model, dd_vae, dd_sampler]
    ).then(
        fn=inc_trigger,
        inputs=[refresh_trigger],
        outputs=[refresh_trigger]
    )
    
    # --- Generation Mode Panel Switching ---
    def toggle_gen_mode_panels(mode):
        return (
            gr.update(visible=(mode == "img2img")),
            gr.update(visible=(mode == "controlnet"))
        )
    
    radio_gen_mode.change(
        fn=toggle_gen_mode_panels,
        inputs=[radio_gen_mode],
        outputs=[panel_img2img, panel_controlnet]
    )
    
    # ControlNet refresh
    btn_refresh_cn.click(
        fn=lambda: (
            gr.update(choices=get_controlnet_models()),
            gr.update(choices=get_controlnet_modules())
        ),
        outputs=[dd_cn_model, dd_cn_module]
    )
    
    # Generation - Main page preset/character batch
    btn_refresh_presets_main.click(
        fn=lambda: gr.update(choices=get_generated_presets() + get_preset_files()),
        outputs=[dd_preset_main]
    )

    dd_preset_main.change(
        fn=load_preset_with_name,
        inputs=[dd_preset_main],
        outputs=[status_box, cbg_active_chars, txt_preset_name, txt_active_order]
    ).then(
        fn=get_active_summary,
        outputs=[txt_active_main]
    )
    
    def validated_generate(
        outfits, morphs, body, styles, set_name, order, prompt, neg,
        gen_mode, template_img, denoising, ignore_height,
        pose_img, cn_module, cn_model, cn_weight, cn_control_mode, 
        cn_pixel_perfect, cn_proc_res, cn_guid_start, cn_guid_end,
        model, vae, cfg_scale, width, height, steps, sampler
    ):
        if set_name and not set_name.strip():
            yield None, "❌ Set name cannot be whitespace if provided!"
            return

        # Generation yield
        yield from generate_characters_batch(
            outfits, morphs, body, styles, set_name, order, prompt, neg,
            generation_mode=gen_mode,
            template_image=template_img,
            denoising_strength=denoising,
            ignore_height_guide=ignore_height,
            pose_image=pose_img,
            cn_module=cn_module,
            cn_model=cn_model,
            cn_weight=cn_weight,
            cn_control_mode=cn_control_mode,
            cn_pixel_perfect=cn_pixel_perfect,
            cn_processor_res=cn_proc_res,
            cn_guidance_start=cn_guid_start,
            cn_guidance_end=cn_guid_end
        )

    btn_gen_chars_main.click(
        fn=validated_generate,
        inputs=[
            dd_outfits_main, dd_morphs_main, dd_body_main, dd_styles_gen, 
            txt_set_name_main, txt_active_order, txt_set_prompt, txt_set_negative,
            radio_gen_mode, img_template, slider_denoising, chk_ignore_height,
            img_pose, dd_cn_module, dd_cn_model, slider_cn_weight, dd_cn_control_mode, 
            chk_cn_pixel_perfect, num_cn_res, slider_cn_start, slider_cn_end,
            dd_model, dd_vae, slider_cfg, num_width, num_height, slider_steps, dd_sampler
        ],
        outputs=[preview, status_box]
    ).then(
        fn=on_generation_complete,
        outputs=[dd_sets]
    )
    
    # Cancel Generation
    btn_cancel_gen.click(
        fn=request_stop_generation,
        inputs=[],
        outputs=[status_box]
    )
    
    
    # Generation Settings
    def update_size_from_dropdown(size_str):
        w, h = size_str.split("x")
        return int(w), int(h)
    
    dd_size.change(
        fn=update_size_from_dropdown,
        inputs=[dd_size],
        outputs=[num_width, num_height]
    )
    
    btn_refresh_lists.click(
        fn=refresh_dropdowns,
        outputs=[dd_model, dd_vae, dd_sampler]
    )
    
    btn_save_settings.click(
        fn=save_gen_config,
        inputs=[
            dd_model, dd_vae, slider_cfg, num_width, num_height, slider_steps, dd_sampler, 
            txt_common_prompt, txt_common_neg, 
            txt_manage_outfits, txt_manage_morphs, txt_manage_body, 
            chk_show_suggestions, dd_cn_control_mode, chk_cn_pixel_perfect, num_cn_res, slider_cn_start, slider_cn_end, dd_merge_format
        ],
        outputs=[settings_status]
    ).then(
        fn=refresh_status,
        outputs=[forge_status, forge_status_server, btn_launch, btn_quick_launch, btn_gen_chars_main, dd_outfits_main, dd_morphs_main, dd_body_main, dd_cn_module]
    )

    # --- FULL SESSION AUTO-SAVE ---
    session_inputs = [
        dd_model, dd_vae, slider_cfg, num_width, num_height, slider_steps, dd_sampler, 
        txt_common_prompt, txt_common_neg,
        dd_outfits_main, dd_morphs_main, dd_body_main, dd_styles_gen,
        txt_set_prompt, txt_set_negative, txt_active_order,
        radio_gen_mode, img_template, slider_denoising, chk_ignore_height,
        img_pose, dd_cn_module, dd_cn_model, slider_cn_weight, dd_cn_control_mode,
        chk_cn_pixel_perfect, num_cn_res, slider_cn_start, slider_cn_end,
        chk_show_suggestions, chk_add_date, dd_merge_format
    ]

    def save_full_session(
        m, v, cfg, w, h, stp, smp, cp, cn,
        outfits, morphs, body, styles,
        sp, sn, order,
        mode, img_t, dens, ign_h,
        img_p, cn_mod, cn_model, cn_w, cn_mode,
        cn_pp, cn_res, cn_guid_start, cn_guid_end,
        show_s, add_d, m_fmt
    ):
        # Stabilize images to prevent /tmp/ expiration
        stable_t = stabilize_image(img_t, "last_template")
        stable_p = stabilize_image(img_p, "last_pose")

        save_gen_config(
            model=m, vae=v, cfg_scale=cfg, width=w, height=h, steps=stp, sampler=smp,
            common_prompt=cp, common_negative=cn,
            active_outfits=outfits, active_morphs=morphs, active_body_parts=body, active_styles=styles,
            set_prompt=sp, set_negative=sn,
            active_character_names=[line.strip() for line in order.split('\n') if line.strip()],
            generation_mode=mode,
            img2img_template=stable_t, img2img_denoising=dens, img2img_ignore_height_guide=ign_h,
            controlnet_pose=stable_p, controlnet_module=cn_mod, controlnet_model=cn_model, controlnet_weight=cn_w, controlnet_control_mode=cn_mode,
            controlnet_pixel_perfect=cn_pp, controlnet_processor_res=cn_res, 
            controlnet_guidance_start=cn_guid_start, controlnet_guidance_end=cn_guid_end,
            merge_format=m_fmt,
            show_suggestions=show_s, add_date_prefix=add_d
        )
        # Also save to lastgen for session recovery
        lastgen_dict = {
            "model": m, "vae": v, "cfg_scale": cfg, "width": w, "height": h, "steps": stp, "sampler": smp,
            "common_prompt": cp, "common_negative": cn,
            "active_outfits": outfits, "active_morphs": morphs, "active_body_parts": body, "active_styles": styles,
            "set_prompt": sp, "set_negative": sn,
            "active_character_names": [line.strip() for line in order.split('\n') if line.strip()],
            "generation_mode": mode,
            "img2img_template": stable_t, "img2img_denoising": dens, "img2img_ignore_height_guide": ign_h,
            "controlnet_pose": stable_p, "controlnet_module": cn_mod, "controlnet_model": cn_model, "controlnet_weight": cn_w, "controlnet_control_mode": cn_mode,
            "controlnet_pixel_perfect": cn_pp, "controlnet_processor_res": cn_res,
            "controlnet_guidance_start": cn_guid_start, "controlnet_guidance_end": cn_guid_end,
            "merge_format": m_fmt,
            "show_suggestions": show_s, "add_date_prefix": add_d
        }
        save_lastgen(lastgen_dict)
        return None

    # Wire to all relevant events
    for comp in [
        dd_model, dd_vae, dd_sampler, radio_gen_mode, 
        dd_outfits_main, dd_morphs_main, dd_body_main, dd_styles_gen,
        dd_outfits_main, dd_morphs_main, dd_body_main, dd_styles_gen,
        chk_ignore_height, chk_show_suggestions, dd_cn_module, dd_cn_model, dd_cn_control_mode,
        chk_cn_pixel_perfect, num_cn_res, slider_cn_start, slider_cn_end,
        dd_merge_format, chk_add_date
    ]:
        comp.change(fn=save_full_session, inputs=session_inputs, outputs=[])
        
    for comp in [slider_cfg, slider_steps, num_width, num_height, slider_denoising, slider_cn_weight]:
        comp.input(fn=save_full_session, inputs=session_inputs, outputs=[])
        
    for comp in [txt_common_prompt, txt_common_neg, txt_set_prompt, txt_set_negative, txt_active_order]:
        comp.blur(fn=save_full_session, inputs=session_inputs, outputs=[])
        
    # Images (template/pose) - save on change
    for comp in [img_template, img_pose]:
        comp.change(fn=save_full_session, inputs=session_inputs, outputs=[])

    # Metadata check
    chk_save_metadata.change(
        fn=lambda meta, url, path, args: save_config(url, path, args, save_metadata=meta),
        inputs=[chk_save_metadata, txt_api_url, txt_forge_path, txt_extra_args],
        outputs=[settings_status]
    )
    # ---------------------------

    
    # Characters tab
    # char_ui_outputs now includes height_guide and model_category after loras
    char_ui_outputs = [txt_char_positive, txt_char_negative, txt_char_loras, dd_height_guide, dd_char_model_category] + outfit_inputs + morph_inputs + body_inputs
    
    btn_refresh_chars.click(
        fn=lambda: gr.update(choices=get_character_files()),
        outputs=[dd_character]
    )
    
    
    def load_character_full(name):
        return load_character_ui(name)

    dd_character.change(
        fn=load_character_full,
        inputs=[dd_character],
        outputs=char_ui_outputs
    )
    
    btn_new_char.click(
        fn=create_new_character,
        inputs=[txt_new_char_name, dd_new_char_cat],
        outputs=[char_status, dd_character]
    ).then(
        fn=load_character_full,
        inputs=[dd_character],
        outputs=char_ui_outputs
    )
    
    # save_inputs now includes height_guide and model_category after loras
    save_inputs = [dd_character, txt_char_positive, txt_char_negative, txt_char_loras, dd_height_guide, dd_char_model_category] + outfit_inputs + morph_inputs + body_inputs
    save_outputs = [char_status, row_futa_warn]
    
    def do_save(*args):
        msg = save_character_from_ui(*args)
        return (msg + " 💚", gr.update(visible=False))
    
    btn_save_char.click(
        fn=do_save,
        inputs=save_inputs,
        outputs=save_outputs
    )
    
    btn_save_char_top.click(
        fn=do_save,
        inputs=save_inputs,
        outputs=save_outputs
    )
    
    btn_rename_char.click(
        fn=rename_character,
        inputs=[dd_character, txt_rename_char],
        outputs=[char_status]
    ).then(
        fn=lambda: gr.update(choices=get_character_files()),
        outputs=[dd_character]
    )
    
    btn_add_outfit.click(
        fn=lambda text: add_config_entry("outfit", text),
        inputs=[txt_add_outfit],
        outputs=[char_status]
    ).then(
        fn=get_outfit_names_text,
        outputs=[txt_manage_outfits]
    ).then(
        fn=lambda: gr.update(choices=get_outfit_choices()),
        outputs=[dd_outfits_main]
    )

    btn_add_morph.click(
        fn=lambda text: add_config_entry("morph", text),
        inputs=[txt_add_morph],
        outputs=[char_status]
    ).then(
        fn=get_morph_names_text,
        outputs=[txt_manage_morphs]
    ).then(
        fn=lambda: gr.update(choices=get_morph_choices()),
        outputs=[dd_morphs_main]
    )
    
    btn_add_body.click(
        fn=lambda text: add_config_entry("body", text),
        inputs=[txt_add_body],
        outputs=[char_status]
    ).then(
        fn=get_body_names_text,
        outputs=[txt_manage_body]
    ).then(
        fn=lambda: gr.update(choices=get_body_choices()),
        outputs=[dd_body_main]
    )
    
    btn_delete_char.click(
        fn=lambda: gr.update(visible=True),
        outputs=[row_delete_confirm]
    )

    btn_cancel_delete.click(
        fn=lambda: gr.update(visible=False),
        outputs=[row_delete_confirm]
    )

    btn_confirm_delete.click(
        fn=delete_character,
        inputs=[dd_character],
        outputs=[char_status]
    ).then(
        fn=lambda: (gr.update(choices=get_character_files()), gr.update(visible=False)),
        outputs=[dd_character, row_delete_confirm]
    ).then(
        fn=lambda: "\n".join([c["name"] for c in get_active_characters()]),
        outputs=[txt_active_order]
    )
    
    # Styles Tab Actions
    btn_refresh_styles.click(
        fn=lambda: gr.update(choices=get_style_files()),
        outputs=[dd_style]
    )
    
    btn_refresh_styles_gen.click(
        fn=lambda: gr.update(choices=get_style_files()),
        outputs=[dd_styles_gen]
    )

    dd_style.change(
        fn=load_style_ui,
        inputs=[dd_style],
        outputs=[txt_style_positive, txt_style_negative, txt_style_loras, dd_style_model_category]
    ).then(
        fn=lambda name: name,
        inputs=[dd_style],
        outputs=[txt_style_name]
    )

    btn_save_style.click(
        fn=save_style,
        inputs=[txt_style_name, txt_style_positive, txt_style_negative, txt_style_loras, dd_style_model_category],
        outputs=[style_status]
    ).then(
        fn=lambda name: (gr.update(choices=get_style_files(), value=name), gr.update(choices=get_style_files())),
        inputs=[txt_style_name],
        outputs=[dd_style, dd_styles_gen]
    )

    btn_save_style_top.click(
        fn=save_style,
        inputs=[txt_style_name, txt_style_positive, txt_style_negative, txt_style_loras, dd_style_model_category],
        outputs=[style_status]
    ).then(
        fn=lambda name: (gr.update(choices=get_style_files(), value=name), gr.update(choices=get_style_files())),
        inputs=[txt_style_name],
        outputs=[dd_style, dd_styles_gen]
    )

    btn_new_style.click(
        fn=create_new_style,
        inputs=[txt_new_style_name, dd_new_style_cat],
        outputs=[style_status, dd_style]
    ).then(
        fn=load_style_ui,
        inputs=[dd_style],
        outputs=[txt_style_positive, txt_style_negative, txt_style_loras, dd_style_model_category]
    ).then(
        fn=lambda name: name,
        inputs=[dd_style],
        outputs=[txt_style_name]
    ).then(lambda: "", outputs=[txt_new_style_name])

    btn_delete_style.click(
        fn=delete_style,
        inputs=[dd_style],
        outputs=[style_status]
    ).then(
        fn=lambda: (gr.update(choices=get_style_files(), value=None), gr.update(choices=get_style_files())),
        outputs=[dd_style, dd_styles_gen]
    )
    
    # Wire body presets
    btn_save_body_preset.click(
        fn=save_body_preset,
        inputs=[txt_body_preset_save_as, dd_body_main],
        outputs=[status_box, dd_body_preset]
    ).then(lambda: "", outputs=[txt_body_preset_save_as]) # Clear name after save
    
    dd_body_preset.change(
        fn=load_body_preset,
        inputs=[dd_body_preset],
        outputs=[dd_body_main]
    )
    
    btn_delete_body_preset.click(
        fn=delete_body_preset,
        inputs=[dd_body_preset],
        outputs=[status_box, dd_body_preset]
    )

    # Wire tag suggestion buttons (Outfits, Morphs, Body)
    for (key, tag), (btn, textbox) in outfit_suggestion_btns.items():
        btn.click(
            fn=lambda current, t=tag: (append_tag(current, t), gr.update(visible=False)),
            inputs=[textbox],
            outputs=[textbox, btn]
        )
    
    for (key, tag), (btn, textbox) in morph_suggestion_btns.items():
        btn.click(
            fn=lambda current, t=tag: (append_tag(current, t), gr.update(visible=False)),
            inputs=[textbox],
            outputs=[textbox, btn]
        )
    
    for (key, tag), (btn, textbox) in body_suggestion_btns.items():
        btn.click(
            fn=lambda current, t=tag: (append_tag(current, t), gr.update(visible=False)),
            inputs=[textbox],
            outputs=[textbox, btn]
        )
    
    # Save show_suggestions toggle
    chk_show_suggestions.change(
        fn=lambda val: save_show_suggestions(val),
        inputs=[chk_show_suggestions],
        outputs=[settings_status]
    )
    
    # Presets
    btn_save_preset.click(
        fn=save_preset,
        inputs=[txt_preset_name],
        outputs=[preset_status]
    ).then(
        fn=lambda: gr.update(choices=get_generated_presets() + get_preset_files()),
        outputs=[dd_preset]
    )

    btn_delete_preset.click(
        fn=delete_preset,
        inputs=[dd_preset],
        outputs=[preset_status]
    ).then(
        fn=lambda: gr.update(choices=get_generated_presets() + get_preset_files(), value=None),
        outputs=[dd_preset]
    ).then(
        fn=lambda: (gr.update(value=""), gr.update(value=[])),
        outputs=[txt_preset_name, cbg_active_chars]
    )
    
    # Sync Logic
    cbg_active_chars.change(
        fn=sync_checks_to_order,
        inputs=[cbg_active_chars, txt_active_order],
        outputs=[txt_active_order]
    ).then(
        fn=set_active_characters_from_list,
        inputs=[cbg_active_chars],
        outputs=[preset_status]
    )

    # Auto-load on dropdown change
    dd_preset.change(
        fn=load_preset_with_name,
        inputs=[dd_preset],
        outputs=[preset_status, cbg_active_chars, txt_preset_name, txt_active_order]
    ).then(
        fn=lambda: gr.update(choices=get_character_files()),
        outputs=[dd_character]
    )

    btn_load_preset.click(
        fn=load_preset_with_name,
        inputs=[dd_preset],
        outputs=[preset_status, cbg_active_chars, txt_preset_name, txt_active_order]
    ).then(
        fn=lambda: gr.update(choices=get_character_files()),
        outputs=[dd_character]
    )
    
    btn_save_preset.click(
        fn=lambda name, text: save_preset(name, [l.strip() for l in text.split('\n') if l.strip()]),
        inputs=[txt_preset_name, txt_active_order],
        outputs=[preset_status]
    ).then(
        fn=lambda: gr.update(choices=get_generated_presets() + get_preset_files()),
        outputs=[dd_preset]
    )
    
    btn_activate_all.click(
        fn=lambda: (activate_all_characters(), get_character_files())[1],
        outputs=[cbg_active_chars]
    )
    
    btn_deactivate_all.click(
        fn=lambda: (deactivate_all_characters(), [])[1],
        outputs=[cbg_active_chars]
    )
    
    btn_new_empty_preset.click(
        fn=lambda: (gr.update(value=""), gr.update(value=[])),
        outputs=[txt_preset_name, cbg_active_chars]
    )
    
    btn_refresh_sets.click(
        fn=lambda: gr.update(choices=list_sets()),
        outputs=[dd_sets]
    )

    btn_new_full_preset.click(
        fn=lambda: (gr.update(value=""), gr.update(value=get_character_files())),
        outputs=[txt_preset_name, cbg_active_chars]
    )
    
    # Forge Server
    btn_launch.click(
        fn=launch_forge,
        inputs=[txt_forge_path, txt_extra_args],
        outputs=[server_status]
    ).then(
        fn=refresh_status,
        outputs=[forge_status, forge_status_server, btn_launch, btn_quick_launch, btn_gen_chars_main, dd_outfits_main, dd_morphs_main, dd_body_main, dd_cn_module]
    ).then(
        fn=refresh_dropdowns,
        outputs=[dd_model, dd_vae, dd_sampler]
    ).then(
        fn=inc_trigger,
        inputs=[refresh_trigger],
        outputs=[refresh_trigger]
    )
    
    btn_kill.click(
        fn=kill_all_forge,
        outputs=[server_status]
    ).then(
        fn=refresh_status,
        outputs=[forge_status, forge_status_server, btn_launch, btn_quick_launch, btn_gen_chars_main, dd_outfits_main, dd_morphs_main, dd_body_main, dd_cn_module]
    ).then(
        fn=inc_trigger,
        inputs=[refresh_trigger],
        outputs=[refresh_trigger]
    )
    
    btn_save.click(
        fn=lambda url, path, args, meta: save_config(url, path, args, save_metadata=meta),
        inputs=[txt_api_url, txt_forge_path, txt_extra_args, chk_save_metadata],
        outputs=[server_status]
    )
    
    # On load
    ui.load(
        fn=refresh_status,
        outputs=[forge_status, forge_status_server, btn_launch, btn_quick_launch, btn_gen_chars_main, dd_outfits_main, dd_morphs_main, dd_body_main, dd_cn_module]
    ).then(
        fn=refresh_dropdowns,
        outputs=[dd_model, dd_vae, dd_sampler]
    ).then(
        fn=lambda: load_body_preset("full body front"),
        outputs=[dd_body_main]
    ).then(
        fn=get_latest_set_preview,
        outputs=[preview]
    ).then(
        fn=preload_session,
        outputs=session_inputs
    )

    def send_set_to_gen(set_name):
        if not set_name:
            return [gr.update() for _ in range(len(session_inputs))] + [gr.update()]
        
        set_data = load_set(set_name)
        if not set_data:
            return [gr.update() for _ in range(len(session_inputs))] + [gr.update()]
        
        gen_cfg = set_data.get("gen_config", {})
        
        # Img2Img / ControlNet images
        set_path = get_set_path(set_name)
        template_path = os.path.join(set_path, "inputs", "template.png")
        pose_path = os.path.join(set_path, "inputs", "pose.png")
        
        results = [
            gen_cfg.get("model", gr.update()),
            gen_cfg.get("vae", gr.update()),
            gen_cfg.get("cfg_scale", gr.update()),
            gen_cfg.get("width", gr.update()),
            gen_cfg.get("height", gr.update()),
            gen_cfg.get("steps", gr.update()),
            gen_cfg.get("sampler", gr.update()),
            gen_cfg.get("common_prompt", gr.update()),
            gen_cfg.get("common_negative", gr.update()),
            gen_cfg.get("active_outfits", gr.update()),
            gen_cfg.get("active_morphs", gr.update()),
            gen_cfg.get("active_body_parts", gr.update()),
            [s for s in gen_cfg.get("active_styles", []) if s in get_style_choices()] if "active_styles" in gen_cfg else gr.update(),
            set_data.get("set_prompt", gr.update()),
            set_data.get("set_negative", gr.update()),
            "\n".join(set_data.get("characters", [])),
            gen_cfg.get("generation_mode", "txt2img"),
            template_path if os.path.exists(template_path) else None,
            gen_cfg.get("img2img_denoising", 0.75),
            gen_cfg.get("img2img_ignore_height_guide", False),
            pose_path if os.path.exists(pose_path) else None,
            gen_cfg.get("controlnet_module", "dw_openpose_full"),
            gen_cfg.get("controlnet_model", ""),
            gen_cfg.get("controlnet_weight", 1.0),
            gen_cfg.get("controlnet_control_mode", "ControlNet is more important"),
            gen_cfg.get("controlnet_pixel_perfect", True),
            gen_cfg.get("controlnet_processor_res", 512),
            gen_cfg.get("controlnet_guidance_start", 0.0),
            gen_cfg.get("controlnet_guidance_end", 1.0),
            gen_cfg.get("show_suggestions", True),
            gen_cfg.get("add_date_prefix", True),
            gen_cfg.get("merge_format", "webp")
        ]
        
        return results + [gr.update(selected="Generation")]

    btn_send_to_gen.click(
        fn=send_set_to_gen,
        inputs=[dd_sets],
        outputs=session_inputs + [tabs]
    )

    # Wire chk_add_date change
    chk_add_date.change(fn=save_full_session, inputs=session_inputs, outputs=[])

    btn_merge.click(
        fn=merge_set_images,
        inputs=[dd_sets, slider_merge_overlap, dd_merge_format],
        outputs=[gr.Image(label="Last Merged", visible=False), merge_status]
    )

if __name__ == "__main__":
    ui.launch(inbrowser=True, server_port=7869, css=css)
