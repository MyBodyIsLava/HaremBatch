# 🚀 HaremBatch

HaremBatch is a batch generation and management tool for Stable Diffusion, optimized for **SDXL**, **Pony**, and **Illustrious** models. It streamlines creating consistent characters, managing outfits, morphs, and styles, while organizing everything into "Sets" (image batches).

> [!NOTE]
> **Maintenance Disclaimer:** HaremBatch was developed as a quick project. No significant future maintenance, updates, or long-term support should be expected.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Character Management** | Create detailed profiles with specific prompts for each outfit, morph, and body part |
| **Styles** | Apply art styles, lighting, or LoRA combinations across multiple characters |
| **Batch Generation** | Generate a full lineup of characters with a single click |
| **Model Categories** | Dedicated support for SDXL, Pony, and Illustrious, with mismatch warnings |
| **Set Editor** | Visualize, rearrange, merge, and refine your generations |
| **Forge Integration** | Seamless connection to SD WebUI Forge via API |
| **Session Recovery** | Automatically saves and restores your last generation settings |

> [!WARNING]
> **HaremBatch does NOT download or install LoRAs automatically.** You must manually download LoRAs from sites like [Civitai](https://civitai.com) and place them in your Forge `models/Lora/` folder before using them in character or style prompts. The exemple use some LoRAs from the [ReZero](https://civitai.com/models/1634464?modelVersionId=1850068) series.

---

## 🛠️ Installation

### Prerequisites

- **Python 3.10** or higher
- **[Stable Diffusion WebUI Forge](https://github.com/lllyasviel/stable-diffusion-webui-forge)** installed and working

### Step 1: Clone the Repository

```bash
git clone https://github.com/MyBodyIsLava/HaremBatch.git
cd HaremBatch
```

---

### Step 2: Create Virtual Environment

#### 🐧 Linux / macOS

```bash
# Create environment
python3 -m venv .venv

# Activate environment
source .venv/bin/activate
```

> [!TIP]
> If `python3` doesn't work, try `python` depending on your setup.

#### 🪟 Windows (PowerShell)

```powershell
# Create environment
python -m venv .venv

# Activate environment
.\.venv\Scripts\Activate.ps1
```

> [!NOTE]
> **Script blocked error?** If PowerShell refuses activation, run this first:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

#### 🪟 Windows (CMD / Command Prompt)

```cmd
# Create environment
python -m venv .venv

# Activate environment
.venv\Scripts\activate.bat
```

---

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

Main dependencies: `gradio`, `requests`, `Pillow`.

---

## 🔗 Connecting to Forge

HaremBatch **does not generate images itself**. It acts as an interface that sends requests to **Stable Diffusion WebUI Forge** via its REST API.

### How Does It Work?

```
┌─────────────────┐        REST API          ┌─────────────────┐
│   HaremBatch    │  ──────────────────────▶ │     Forge       │
│   (Interface)   │  ◀────────────────────── │  (Generation)   │
└─────────────────┘      Generated images    └─────────────────┘
```

1. **HaremBatch** builds complete prompts (character + outfit + morph + style + common prompts)
2. **Forge** receives the request and generates the image using your GPU
3. **The image** is sent back to HaremBatch, which saves and organizes it

### Preparing Forge

1. **Enable the API**: Launch Forge with the `--api` argument:
   ```bash
   # Linux example
   ./webui.sh --api
   
   # Windows example
   webui-user.bat  # (add --api to COMMANDLINE_ARGS in the file)
   ```

2. **Default port**: Forge listens on `http://127.0.0.1:7860`

### Connecting HaremBatch to Forge

1. Launch HaremBatch:
   ```bash
   python main.py
   ```

2. Go to the **⚙️ Forge Server** tab

3. Enter your Forge API URL (default: `http://127.0.0.1:7860`)

4. Click **🔄 Refresh** to verify the connection

> [!IMPORTANT]
> Forge must be **running** before you can generate images. The status indicator in HaremBatch shows whether the connection is established.

### Configuring the Launch Forge Button

HaremBatch can **automatically launch Forge** for you. This is optional but convenient.

1. In the **⚙️ Forge Server** tab, find the **Forge Path** field
2. Enter the **full path** to your Forge launch script:

| OS | Example Path |
|----|--------------|
| **Linux** | `/home/username/stable-diffusion-webui-forge/webui.sh` |
| **Windows** | `C:\AI\stable-diffusion-webui-forge\webui-user.bat` |

3. **(Optional)** Add **Extra Arguments** in the field below:
   - Default: `--api --listen --nowebui`
   - `--api` → Required for HaremBatch to communicate
   - `--listen` → Allows connections from other devices
   - `--nowebui` → Disables the browser UI (faster startup)

4. Click **🚀 Launch Forge** to start Forge directly from HaremBatch

> [!TIP]
> If you always use the same settings, configure this once and HaremBatch will remember it.

---

## 📖 Quick Start Guide

This guide walks you through creating your first character, style, preset, and set.

### 1. 🎭 Creating a Character

A **character** contains all the information needed to generate a consistent person: physical appearance, possible outfits, and variations (morphs).

1. Go to the **📂 Characters** tab
2. Click **➕ New Character**
3. Fill in the fields:

| Field | Description | Example |
|-------|-------------|---------|
| **Name** | Character name | `Rem` |
| **Positive Prompt** | Base prompt with LoRA and gender tag | `<lora:Rem_IlluXL:0.8> 1girl, rem (re:zero)` |
| **Negative Prompt** | What you DON'T want to see (optional) | `ugly, deformed` |

> [!IMPORTANT]
> **Always include the gender tag** (`1girl`, `1boy`, etc.) in the character's base prompt. Morphs like `futa` or `male` will override it using the `-"TAG"` syntax (see below).

4. **Body**: Describe body parts
   - `skin_color` → `fair skin`
   - `eyes` → `blue eyes`
   - `hair_color` → `blue hair`
   - `breast` → `medium breasts`
   - etc.

5. **Outfits**: Add clothing variations
   - `fully_clothed` → `maid dress, white apron, black dress`
   - `fully_naked` → `nude, naked`
   - `swimsuit` → `school swimsuit`

6. **Morphs**: Add transformations using `-"TAG"` to remove conflicting tags
   - `futa` → `1futa, -"1girl", futanari, penis`
   - `male` → `1boy, -"1girl", -"pussy", male focus`
   - `pregnant` → `pregnant, large belly`

> [!TIP]
> The `-"TAG"` syntax removes a tag from earlier in the prompt. This prevents conflicts like having both `1girl` and `1boy` in the same prompt.

7. Click **💾 Save Character**

> [!TIP]
> The **LoRA Links** field at the bottom lets you note Civitai URLs of your LoRAs for reference. It doesn't affect generation.

---

### 2. 🎨 Creating a Style

A **style** is a prompt preset that applies to ANY character. Ideal for applying an art style, lighting, or visual concept. No LoRA required but they work as well!

1. Go to the **🎨 Styles** tab
2. Enter a name in the **Create New Style** field (e.g., `Manga Style`)
3. Select the **Model Category**
4. Click **➕ Create**
5. Fill in the prompts:

**Example: Manga Style (no LoRA required)**
| Field | Value |
|-------|-------|
| **Name** | `Manga Style` |
| **Model Category** | `Illustrious` |
| **Positive Prompt** | `manga, monochrome, greyscale, screentone, halftone, comic, lineart` |
| **Negative Prompt** | `color, colorful, painted, 3d` |

**Example: Anime Style (no LoRA required)**
| Field | Value |
|-------|-------|
| **Name** | `Anime Style` |
| **Model Category** | `Illustrious` |
| **Positive Prompt** | `anime, anime style, cel shading, vibrant colors, clean lines` |
| **Negative Prompt** | `realistic, photorealistic, 3d render` |

4. Click **💾 Save Style**

> [!NOTE]
> During generation, you can select **multiple styles** that will all be combined in the final prompt.

---

### 3. 📋 Creating an Active Preset

A **preset** lets you save which characters are **active** (selected for generation). Useful if you have many characters and want to quickly switch between different groups.

1. Go to the **📂 Characters** or **🚀 Generation** tab
2. Check the characters you want to activate (e.g., Rem and Ram)
3. In the **Presets** section (at the top), enter a name (e.g., `ReZero`)
4. Click **💾 Save Preset**

**To load a preset:**
- Select it from the dropdown
- The corresponding characters will be automatically checked

**Example preset file (`presets/ReZero.json`):**
```json
{
  "active": ["Rem", "Ram"]
}
```

---

### 4. 🖼️ Creating a Set (Generating Images)

A **Set** is a batch of images generated together. HaremBatch automatically creates a folder with all images from the batch.

1. Go to the **🚀 Generation** tab
2. Configure:

| Option | Description |
|--------|-------------|
| **Common Prompt** | Prompt added to ALL generations (pose, action, etc.) |
| **Common Negative** | Negative added to all generations |
| **Outfits** | Check outfits to generate |
| **Morphs** | Check morphs to apply |
| **Styles** | Select art styles |

3. **(Optional)** Give the set a name in the **Set Name** field
   - If empty, the common prompt will be used as the name
   - A timestamp is automatically added at the beginning (e.g., `20251228_143500_my_set`)

4. Click **🚀 GENERATE**

5. Images appear in `output/YourSetName/`

**To view and modify a set:**
1. Go to the **📁 Set Editor** tab
2. Select your set from the list
3. You can:
   - Navigate between images (← → arrows)
   - Delete an image
   - Regenerate a specific image
   - Rearrange order
   - Export the set

---

## ⚙️ Generation Settings

Before generating, you need to configure some important settings. Go to the **🚀 Generation** tab.

### Model Selection (Requires Forge Online)

The **Model** dropdown lists all checkpoints available in Forge. This requires Forge to be connected.

- Select a model matching your character's category (Illustrious, Pony, or SDXL)
- If model and character category don't match, you'll see a warning

### Core Settings

| Setting | Description | Recommended |
|---------|-------------|-------------|
| **Steps** | Number of diffusion steps. More = better quality but slower | 20-30 |
| **CFG Scale** | How closely to follow the prompt. Higher = more literal | 5-7 |
| **Width / Height** | Image dimensions. Use SDXL-compatible sizes | 832×1216 (portrait) |
| **Sampler** | Algorithm for generation | Euler a, DPM++ 2M |

### Prompt Hierarchy Example

HaremBatch handles prompts at different levels to separate character details from general poses and quality tags.

| Prompt Level | Set In | Purpose |
|--------------|--------|---------|
| **Global (Common)** | ⚙️ Forge Server tab | Quality tags and universal negatives applied to ALL generations. |
| **Set (Batch)** | 🚀 Generation tab | Poses, actions, and scene details specific to the current batch. |
| **Character/Style** | Respective Editor tabs | Core identity and art style definitions. |

#### Concrete Example

**Global Settings (Common)** - Things you ALWAYS want:
```
Common Prompt: score_9, score_8_up, masterpiece, best quality, detailed, highres
Common Negative: bad quality, worst quality, watermark, censored, text
```

**Generation Tab (Set)** - Things specific to THIS batch:
```
Set Prompt: standing, full body, looking at viewer, simple background
Set Negative: sitting, lying down
```

> [!TIP]
> Keep **Common Prompts** general (quality tags). Put poses and actions in **Set Prompt** so each batch can have different poses without editing your settings.

---

## 🧍 Understanding the Layer System

HaremBatch builds prompts using a **layered system**. Each layer adds specific tags that combine into the final prompt. Understanding this system is key to getting good results.

### The Complete Layer Order

When generating, HaremBatch builds the final prompt by combining **7 layers** in this exact order:

```
1. Common Prompt     →  Quality tags (applies to ALL sets)
2. Character Base    →  LoRA + character name + gender
3. Body Parts        →  Physical attributes (breast size, hair color...)
4. Morph             →  Body transformation (futa, male, pregnant...)
5. Outfit            →  Clothing or nudity state
6. Style             →  Art style (manga, anime, lighting...)
7. Set Prompt        →  Pose/action for THIS batch
```

Each layer can add, modify, or suppress tags from previous layers using the `-"TAG"` syntax (e.g., `-"1girl"` to remove a tag).

### Layer-by-Layer Explanation

#### 1️⃣ Common Prompt (Settings → Forge Server tab)
**What it should contain:** Quality tags that apply to ALL your generations, ALL sets.

```
score_9, score_8_up, masterpiece, best quality, detailed, highres
```
 
> [!NOTE]
> This is set once and rarely changed. Keep it general.
 
---
 
#### 2️⃣ Character Base (Character Editor → Positive Prompt)
**What it should contain:** LoRA trigger, character name/tag, gender tag
 
```
<lora:Rem_IlluXL:0.8> 1girl, rem (re:zero)
```
 
> [!IMPORTANT]
> Always include the gender tag here. Morphs will override it if needed.
 
---
 
#### 3️⃣ Body Parts (Generation tab → Body Parts checkboxes)
**What it should contain:** Physical attributes you want to apply. Only checked body parts are included.
 
**Key principle:** Body parts describe the body itself, NOT clothing or accessories.
 
| Body Part | Good | Bad (creates conflict) |
|-----------|------|------------------------|
| `feet` | `toes, arched feet` | `bare feet` ← conflicts with clothed outfits |
| `back` | `spine, shoulder blades` | `bare back` ← conflicts with clothed outfits |
| `breast` | `large breasts` | `exposed breasts` ← that's an outfit thing |
 
---
 
#### 4️⃣ Morphs (Character Editor → Morphs section)
**What it should contain:** Body transformations and gender changes.
 
| Morph | What it does | Example |
|-------|--------------|---------|
| `female` | Ensure female appearance | `1girl` |
| `male` | Change to male | `1boy, -"1girl", -"pussy", male focus` |
| `futa` | Futanari (female + penis) | `1futa, -"1girl", futanari, penis` |
| `pregnant` | Add pregnancy | `pregnant, large belly` |
| `transformation` | Character-specific form (demon, oni, etc.) | `single horn, glowing eyes` |
 
---
 
#### 5️⃣ Outfits (Character Editor → Outfits section)
**What it should contain:** Clothing and accessories. Each outfit is a complete description of what the character is wearing.
 
| Outfit | Purpose | Example |
|--------|---------|---------|
| `fully_clothed` | Complete outfit with all clothes | `dress, skirt, thighhighs, gloves` |
| `fully_naked` | Completely nude, no accessories | `nude, naked, fully nude` |
| `virtually_naked` | Nude but with **signature accessories** that don't cover breasts/crotch | `nude, blindfold, hairband` (for 2B) |
| `topless` | No top, but bottom clothes remain | `topless, skirt, thighhighs` |
| `bottomless` | No bottom, but top clothes remain | `bottomless, shirt, bra` |
| `swimsuit` | Beach/pool attire | `bikini, one-piece swimsuit` |
 
---
 
#### 6️⃣ Styles (Generation tab → Styles dropdown)
**What it should contain:** Art style, lighting, or visual effects that apply on top of everything.
 
```
manga, monochrome, screentone, lineart
```
 
---
 
#### 7️⃣ Set Prompt (Generation tab)
**What it should contain:** Pose, action, scene, background for THIS specific batch.
 
```
standing, full body, looking at viewer, simple background
```
 
---
 
## 📖 Standardization Guide
 
To maintain consistency across your character library, follow these standard definitions for the default layers.
 
### 🤖 Model Category
| Category | Description |
|:---|:---|
| `Illustrious` | For Illustrious/NoobAI based models (Standard) |
| `Pony` | For Pony Diffusion V6 based models |
| `SDXL` | For standard SDXL 1.0 based models |

---

### 👗 Default Outfits
| Key | Display Name | Content Recommendation |
|:---|:---|:---|
| `fully_clothed` | fully clothed | The character's signature full outfit (dress, armor, wings, etc.) |
| `virtually_naked` | virtually naked | Nude, but keeps **identifying accessories** (blindfold, headband, gloves) |
| `fully_naked` | fully naked | Completely nude, no accessories at all |
| `topless` | topless | No top/bra, but lower clothes (skirt, pants) and shoes remain |
| `bottomless` | bottomless | No pants/panties, but top/shirt and socks/boots remain |
| `full_underwear` | full underwear | Matching bra and panties set |
| `panties_only` | panties only | Just panties, no top |
| `bra_only` | bra only | Just bra, no bottom |
| `swimsuit` | swimsuit | Bikini, school swimsuit, or competition suit |
| `work` | work | Alternative work or casual outfit (suit, uniform) |

---

### 🧬 Default Morphs
| Key | Display Name | Content Recommendation |
|:---|:---|:---|
| `female` | female | `1girl`. Gender swap for males. |
| `male` | male | `1boy, -"1girl", -"pussy", male focus`. Gender swap for females. |
| `futa` | futa | `1futa, -"1girl", futanari, penis`. Female with penis. |
| `full_futa` | full futa | `1futa, -"1girl", futanari, penis, pussy, balls`. Futa with balls and pussy. |
| `trap` | trap | `trap, crossdressing, feminine male, -"1girl"`. Androgynous male form with penis|
| `pregnant` | pregnant | `pregnant, large belly`. Pregnancy morph. |
| `transformation` | transformation | `single horn, glowing eyes` or any character-specific change. |

---

### 🧍 Default Body Parts
*Recommendations to avoid conflicts with outfits:*

| Category | Key | Recommendation |
|:---|:---|:---|
| **Skin/Eyes** | `skin_color`, `eyes` | Simple tags: `pale skin`, `blue eyes` |
| **Hair** | `head`, `hair_length`, `hair_color` | `long hair`, `bob cut`, `pink hair` |
| **Torso** | `breast`, `nipples`, `abdomen`, `back` | `large breasts`, `toned abs` (Avoid `bare back/skin`) |
| **Lower** | `ass`, `pussy`, `anus`, `penis`, `legs`, `feet` | `round ass`, `thick thighs` (Avoid `bare feet`) |
| **Special** | `hands_nails`, `armpits`, `tattoos`, `jewelry` | `painted nails`, `navel piercing`, `tribal tattoo` |

> [!IMPORTANT]
> **Canon body type rule:** Body parts should describe the character's **canonical** form.
> - **Female characters:** Leave `penis` empty. Fill `pussy` if needed.
> - **Male characters:** Leave `pussy` empty. Fill `penis` if needed.
> - Morphs (`futa`, `male`, `trap`) will add the appropriate anatomy when applied.

---

### Avoiding Tag Conflicts

**The Golden Rule**: Don't define the same thing in multiple places.

#### ❌ Bad Example (Conflict)
```
Character Base: "1girl, rem, medium breasts"
Body Part (breast): "large breasts"
```
Result: Both tags appear → Stable Diffusion gets confused

#### ✅ Good Example (No Conflict)
```
Character Base: "1girl, rem"
Body Part (breast): "medium breasts"
```
Now you can change breast size per-generation without editing the character

### When to Use Body Parts vs Character Base

| Put in Character Base | Put in Body Parts |
|----------------------|-------------------|
| LoRA trigger words | Breast size |
| Character name/tag | Hair color/length |
| Signature features that NEVER change | Eye color |
| | Skin color |
| | Body details you might want to vary |

### View-Specific Tags

Not all body parts are visible in every pose. Select only relevant ones:

| Pose/View | Useful Body Parts | Avoid |
|-----------|-------------------|-------|
| **Front view** | eyes, breast, abdomen, pussy, penis, legs | ass, back, anus |
| **Back view** | back, ass, anus, legs | breast, pussy, abdomen |
| **Portrait** | eyes, head, hair | legs, feet, ass |
| **Full body** | All visible parts | — |

> [!IMPORTANT]
> Including `ass` tags in a front-facing image can cause visual artifacts or unwanted anatomy appearing where it shouldn't be.

---

## 📦 Body Presets

**Body Presets** are saved combinations of body parts that you can quickly apply. Instead of manually checking 10+ body parts every time, save them as a preset.

### Built-in Presets

| Preset | Body Parts Included |
|--------|---------------------|
| **full body front** | skin_color, eyes, head, hair_length, hair_color, breast, nipples, abdomen, pussy, penis, legs, feet, hands_nails, armpits, jewelry, tattoos |
| **full body back** | skin_color, hair_length, hair_color, back, ass, anus, legs, feet, jewelry, tattoos |
| **portrait only** | skin_color, eyes, head, hair_length, hair_color, jewelry, tattoos, breast, nipples |

### Using Body Presets

1. In the **🚀 Generation** tab, find the **Body Preset** dropdown
2. Select a preset → The corresponding body parts are automatically checked
3. You can still manually adjust after selecting a preset

### Creating Custom Presets

Body presets are defined in `generation_config.json` under `body_presets`:

```json
{
  "body_presets": {
    "full body front": ["skin_color", "eyes", "head", "breast", "nipples", "abdomen", "pussy", "penis", "legs", "feet"],
    "full body back": ["skin_color", "back", "ass", "anus", "legs", "feet"],
    "portrait only": ["skin_color", "eyes", "head", "hair_length", "hair_color", "jewelry", "tattoos", "breast", "nipples"]
  }
}
```

> [!TIP]
> Create presets for your most common poses to speed up your workflow!

---

## 📁 File Structure

```
HaremBatch/
├── characters/              # Character JSON files
│   ├── Rem.json             # Re:Zero character
│   ├── Ram.json             # Re:Zero character  
│   └── 2B.json              # Nier Automata character
├── styles/                  # Style JSON files (no LoRA required)
│   ├── Manga Style.json     # Monochrome manga look
│   └── Anime Style.json     # Vibrant anime look
├── presets/                 # Saved character selections
│   └── ReZero.json          # Activates Rem + Ram
├── templates/               # Base images for img2img
├── inputs/                  # Input images folder
├── output/                  # Generated sets
│   └── 20251228_standing/   # Timestamped set folder
├── main.py                  # Gradio interface (entry point)
├── generation.py            # Generation logic
├── forge.py                 # Forge API communication
├── config.py                # Configuration management  
├── data.py                  # Constants and defaults
└── requirements.txt         # Python dependencies
```

---

## 🎮 Generation Modes

| Mode | Description | Stability |
|------|-------------|-----------|
| **txt2img** | Classic text-to-image generation | ✅ Stable |
| **img2img** | Uses a base image (template) as starting point | ✅ Stable |
| **controlnet** | Uses ControlNet to control the pose | ⚠️ Experimental |

### ControlNet Settings

When using `controlnet` mode, additional options appear:

- **Preprocessor**: `dw_openpose_full` is **highly recommended** for Anime/Manga characters as it detects poses much better than standard OpenPose.
- **Control Mode**:
  - `Balanced`: Equal importance to prompt and pose.
  - `My prompt is more important`: Prioritizes your prompt (style, details) over exact pose match.
  - `ControlNet is more important`: Prioritizes the pose skeleton (recommended for complex poses).

### Recommended ControlNet Models

For best results with Illustrious/SDXL based models, use these specific ControlNet model:
- **[Illustrious XL ControlNet OpenPose](https://civitai.com/models/1359846/illustrious-xl-controlnet-openpose)**

> [!TIP]
> Place these `.safetensors` files in your Forge `models/ControlNet/` folder.

---

## ❓ FAQ / Troubleshooting

### Connection Issues

#### "Connection failed" in Forge Server tab
**Symptoms:** Red status indicator, can't select models or generate

**Solutions:**
1. **Verify Forge is running** - Check your terminal/console for Forge output
2. **Check the API flag** - Forge must be launched with `--api`:
   ```bash
   ./webui.sh --api          # Linux
   webui-user.bat            # Windows (add --api to COMMANDLINE_ARGS)
   ```
3. **Verify the URL** - Default is `http://127.0.0.1:7860`. If you changed the port, update it
4. **Check firewall** - Windows Firewall or antivirus may block the connection
5. **Try a different port** - Forge might be on 7861, 7862, etc. if you have multiple instances

#### "Cannot load model list"
**Cause:** Forge is starting up or the models folder is empty

**Solutions:**
1. Wait for Forge to fully load (watch for "Running on local URL" message)
2. Click **🔄 Refresh** again after Forge finishes loading

---

### Generation Issues

#### Images don't generate / Nothing happens
**Checklist:**
- [ ] Is Forge connected? (Check status indicator)
- [ ] Is at least one character **active** (checked)?
- [ ] Is at least one **outfit** selected?
- [ ] Is a **model** selected in the dropdown?
- [ ] Does the model exist in Forge? (Check Forge console for errors)

#### "Model category mismatch" warning
**Cause:** The character's LoRA is for one model type (e.g., Illustrious) but you loaded a different type (e.g., Pony)

**Solutions:**
1. Change the model in Forge to match the character's category
2. Or change the character's category in the Character Editor

#### Generated images look wrong / artifacts
**Common causes:**
- **Conflicting tags** - Same thing defined in multiple places (e.g., breast size in base AND body parts)
- **Wrong body parts for view** - Using `ass` tags in a front-facing pose
- **LoRA not loaded** - Check Forge console for "LoRA not found" errors

> [!TIP]
> **Debug with image metadata!** Right-click any generated image and check its metadata (in Forge or an image viewer). You'll see the complete prompt that was used. Check if:
> - All expected tags are present
> - No conflicting tags appear (e.g., both `1girl` and `1boy`)
> - LoRA syntax is correct (`<lora:Name:0.8>`)
> - No missing or extra tags

---

### LoRA Issues

#### "LoRA not found" / LoRA not applying
**Cause:** The LoRA file is missing from your Forge installation

**Solutions:**
1. Download the LoRA from Civitai (link is in the character's LoRA Links field)
2. Place the `.safetensors` file in your Forge folder: `models/Lora/`
3. Restart Forge or click refresh in the LoRA menu
4. Verify the LoRA name in the prompt matches the filename (without extension)

#### LoRA has no effect
**Possible causes:**
- Weight too low (try `<lora:Name:0.8>` instead of `<lora:Name:0.3>`)
- Missing trigger words (check the LoRA's Civitai page for required tags)
- Wrong model type (Illustrious LoRA on Pony model won't work well)

---

### Character Issues

#### Morphs don't change gender properly
**Cause:** The `-"TAG"` syntax might be wrong, or the base tag isn't being removed

**Check:**
- Base prompt has `1girl` (or `1boy`)
- Male morph has `-"1girl"` and `-"pussy"` to remove female tags
- Futa morph has `-"1girl"` and adds `1futa`

#### Outfit and body parts conflict
**Example:** Character has `bare feet` in body parts, but you want them clothed with shoes

**Solution:** Don't use "bare" or "exposed" terms in body parts. Those belong in outfits.

---

### Performance Issues

#### Generation is very slow
**Solutions:**
1. Reduce **Steps** (20 is usually enough for testing)
2. Reduce image **Width/Height**
3. Close other GPU-intensive applications
4. Check Forge console for out-of-memory errors

#### HaremBatch freezes during generation
**Cause:** Long generations can make the UI unresponsive

**Note:** This is normal for batch generation. The UI will update when images complete.

---

## ⚖️ License

MIT License - Created by **MyBodyIsLava**.
