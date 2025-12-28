# forge.py - Forge detection, launching, and API communication
import os
import time
import platform
import signal
import subprocess
import atexit
import requests
import socket
import gradio as gr

from config import load_config, get_outfit_choices, get_morph_choices, get_body_choices
from data import COMMON_PORTS

# Track launched Forge process
forge_process = None

def is_windows():
    return platform.system() == "Windows"

# --- FORGE DETECTION ---

def is_forge_api(url):
    """Check if URL is a valid Forge/A1111 API."""
    try:
        response = requests.get(f"{url}/sdapi/v1/options", timeout=5)
        return response.status_code == 200
    except:
        return False

def find_forge():
    """Find Forge on configured URL or common ports."""
    config = load_config()
    
    if is_forge_api(config["api_url"]):
        return True, config["api_url"]
    
    for port in COMMON_PORTS:
        url = f"http://127.0.0.1:{port}"
        if url != config["api_url"] and is_forge_api(url):
            return True, url
    
    return False, None

def get_forge_status_text():
    """Get Forge status string."""
    online, url = find_forge()
    if online:
        return f"🟢 ONLINE ({url})"
    return "🔴 OFFLINE"

def get_current_model():
    """Get currently loaded model from Forge."""
    online, url = find_forge()
    if not online:
        return ""
    try:
        response = requests.get(f"{url}/sdapi/v1/options", timeout=5)
        if response.status_code == 200:
            return response.json().get("sd_model_checkpoint", "")
    except:
        pass
    return ""

def get_models_list():
    """Get list of available models from Forge."""
    online, url = find_forge()
    if not online:
        return []
    try:
        response = requests.get(f"{url}/sdapi/v1/sd-models", timeout=5)
        if response.status_code == 200:
            return [m["title"] for m in response.json()]
    except:
        pass
    return []

def get_vae_list():
    """Get list of available VAEs from Forge."""
    online, url = find_forge()
    if not online:
        return ["Automatic", "None"]
    try:
        response = requests.get(f"{url}/sdapi/v1/sd-vae", timeout=5)
        if response.status_code == 200:
            vaes = ["Automatic", "None"] + [v["model_name"] for v in response.json()]
            return vaes
    except:
        pass
    return ["Automatic", "None"]

def get_samplers_list():
    """Get list of available samplers from Forge."""
    online, url = find_forge()
    if not online:
        return ["Euler a", "Euler", "DPM++ 2M", "DPM++ 2M Karras", "DPM++ SDE Karras"]
    try:
        response = requests.get(f"{url}/sdapi/v1/samplers", timeout=5)
        if response.status_code == 200:
            return [s["name"] for s in response.json()]
    except:
        pass
    return ["Euler a", "Euler", "DPM++ 2M", "DPM++ 2M Karras", "DPM++ SDE Karras"]

def refresh_dropdowns():
    """Refresh model/vae/sampler dropdowns with current values."""
    models = get_models_list()
    vaes = get_vae_list()
    samplers = get_samplers_list()
    current_model = get_current_model()
    
    return (
        gr.update(choices=models, value=current_model if current_model else None),
        gr.update(choices=vaes),
        gr.update(choices=samplers)
    )

def refresh_status():
    """Refresh status, button states and dropdown choices."""
    online, url = find_forge()
    status = f"🟢 ONLINE ({url})" if online else "🔴 OFFLINE"
    
    outfit_choices = get_outfit_choices()
    morph_choices = get_morph_choices()
    body_choices = get_body_choices()
    
    return (
        status, 
        status, 
        gr.update(interactive=not online),  # btn_launch
        gr.update(visible=not online),  # btn_quick_launch
        gr.update(interactive=online),  # btn_gen_chars_main
        gr.update(choices=outfit_choices),
        gr.update(choices=morph_choices),
        gr.update(choices=body_choices),
        # Toggle Preprocessor interactivity based on Forge status
        gr.update(interactive=online) # dd_cn_module
    )

# --- FORGE LAUNCHER ---

def kill_forge():
    """Kill Forge process if running."""
    global forge_process
    if forge_process is not None:
        try:
            if is_windows():
                forge_process.terminate()
            else:
                os.killpg(os.getpgid(forge_process.pid), signal.SIGTERM)
            print("🛑 Forge process terminated")
        except:
            pass
        forge_process = None

def kill_all_forge():
    """Kill all Forge/SD processes."""
    kill_forge()
    try:
        if is_windows():
            os.system("taskkill /F /IM python.exe /FI \"WINDOWTITLE eq *webui*\" 2>nul")
        else:
            os.system("pkill -f 'webui.*--api' 2>/dev/null")
            os.system("pkill -f 'launch.py' 2>/dev/null")
        return "🛑 Kill signal sent to all Forge processes"
    except Exception as e:
        return f"❌ Error: {str(e)}"

atexit.register(kill_forge)

def is_port_free(port):
    """Check if a port is free."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) != 0

def launch_forge(forge_path, extra_args):
    """Launch Forge with specified arguments (cross-platform, isolated from current venv)."""
    global forge_process
    
    if not forge_path or not os.path.exists(forge_path):
        return "❌ Error: Launcher path not found!"

    args_list = extra_args.split() if extra_args else []
    working_dir = os.path.dirname(forge_path)
    
    clean_env = os.environ.copy()
    clean_env.pop("VIRTUAL_ENV", None)
    clean_env.pop("PYTHONHOME", None)
    clean_env.pop("PYTHONPATH", None)
    if "VIRTUAL_ENV" in os.environ:
        venv_bin = os.path.join(os.environ["VIRTUAL_ENV"], "bin")
        clean_env["PATH"] = clean_env["PATH"].replace(venv_bin + ":", "").replace(venv_bin, "")
    
    try:
        if is_windows():
            if forge_path.endswith('.bat'):
                cmd = [forge_path] + args_list
            else:
                cmd = ["python", forge_path] + args_list
            
            forge_process = subprocess.Popen(
                cmd,
                cwd=working_dir,
                env=clean_env,
                stdout=None,
                stderr=None,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:
            if forge_path.endswith('.sh'):
                cmd = ["bash", forge_path] + args_list
            else:
                cmd = ["python", forge_path] + args_list
            
            forge_process = subprocess.Popen(
                cmd,
                cwd=working_dir,
                env=clean_env,
                stdout=None,
                stderr=None,
                start_new_session=True
            )
        
        print(f"🚀 Launched: {' '.join(cmd)}")
        
        for status in wait_for_forge():
            yield status
        
    except Exception as e:
        yield f"❌ Error: {str(e)}"

def wait_for_forge(timeout=120):
    """Wait for Forge to come online."""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        elapsed = int(time.time() - start_time)
        online, url = find_forge()
        
        if online:
            yield f"✅ Forge is ready! ({url})"
            return
        
        yield f"⏳ Waiting for Forge... ({elapsed}s)"
        time.sleep(3)
    
    yield "❌ Timeout waiting for Forge"

# --- CONTROLNET API ---

def get_controlnet_models():
    """Get list of available ControlNet models from Forge."""
    online, url = find_forge()
    if not online:
        return []
    try:
        response = requests.get(f"{url}/controlnet/model_list", timeout=5)
        if response.status_code == 200:
            data = response.json()
            # API returns {"model_list": [...]}
            return data.get("model_list", [])
    except:
        pass
    return []

def get_controlnet_modules():
    """Get list of available ControlNet preprocessor modules from Forge."""
    online, url = find_forge()
    if not online:
        # Return common OpenPose modules as fallback
        return ["openpose", "openpose_face", "openpose_hand", "openpose_full", "dw_openpose_full", "canny", "depth", "lineart", "none"]
    try:
        response = requests.get(f"{url}/controlnet/module_list", timeout=5)
        if response.status_code == 200:
            data = response.json()
            # Return all modules without filtering
            modules = data.get("module_list", [])
            return modules if modules else ["openpose", "openpose_full", "dw_openpose_full", "none"]
    except:
        pass
    return ["openpose", "openpose_face", "openpose_hand", "openpose_full", "dw_openpose_full", "canny", "depth", "lineart", "none"]

def refresh_controlnet_dropdowns():
    """Refresh ControlNet model and module dropdowns."""
    import gradio as gr
    models = get_controlnet_models()
    modules = get_controlnet_modules()
    return (
        gr.update(choices=models, value=models[0] if models else None),
        gr.update(choices=modules, value="openpose_full" if "openpose_full" in modules else (modules[0] if modules else None))
    )
