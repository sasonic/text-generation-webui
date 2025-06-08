import gradio as gr
import chatterbox
import time
from pathlib import Path
import traceback
import torch
import torchaudio
import html
import json

# --- Directories and Files ---
EXTENSION_DIR = Path("extensions/chatterbox_tts")
VOICES_DIR = EXTENSION_DIR / "voices"
SETTINGS_FILE = EXTENSION_DIR / "settings.json"

# --- Default Parameters ---
params = {
    "activate": False,
    "selected_voice": "Default Voice",
    "temperature": 0.7,
    "exaggeration": 0.5,
    "cfg_weight": 0.5,
    "playback_rate": 1.0,
}

# --- Settings Persistence ---
def save_settings():
    """Saves the current `params` dictionary to the settings file."""
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(params, f, indent=4)

def load_settings():
    """Loads settings from the file and updates the `params` dictionary."""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, 'r') as f:
                loaded_params = json.load(f)
                for key in list(loaded_params.keys()):
                    if key not in params:
                        del loaded_params[key]
                params.update(loaded_params)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Chatterbox: Could not load settings, using defaults. Error: {e}")

# --- Internal Variables ---
tts_model = None

def initialize_tts():
    """Loads the TTS model into memory only when first needed."""
    global tts_model
    if tts_model is not None:
        return
    print("Initializing Chatterbox TTS...")
    try:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Chatterbox: Using device: {device}")
        tts_model = chatterbox.ChatterboxTTS.from_pretrained(device=device)
        print("Chatterbox TTS model initialized successfully.")
    except Exception as e:
        tts_model = None
        print(f"Error initializing Chatterbox TTS model: {e}")
        traceback.print_exc()
        print("The plugin will be disabled.")

def ensure_output_dir():
    (EXTENSION_DIR / "outputs").mkdir(parents=True, exist_ok=True)
    return EXTENSION_DIR / "outputs"

def get_voice_files():
    VOICES_DIR.mkdir(parents=True, exist_ok=True)
    files = [p.name for p in VOICES_DIR.glob("*") if p.suffix in (".wav", ".mp3")]
    return ["Default Voice"] + files

def ui():
    """Creates the user interface elements for the extension."""
    with gr.Accordion("Chatterbox TTS", open=True):
        gr.Markdown("High-quality, realistic TTS using [Resemble AI's Chatterbox](https://github.com/resemble-ai/chatterbox).")
        
        with gr.Row():
            activate_checkbox = gr.Checkbox(value=params["activate"], label="Activate Chatterbox TTS")

        with gr.Row():
            voice_dropdown = gr.Dropdown(
                label="Custom Voice", choices=get_voice_files(), value=params["selected_voice"],
                info="Select a voice file from your 'voices' folder."
            )
            refresh_button = gr.Button("Refresh Voices")
        
        gr.Markdown("Advanced Voice Settings")
        with gr.Row():
            temperature_slider = gr.Slider(
                minimum=0.1, maximum=1.0, step=0.05, label="Temperature", value=params["temperature"],
                info="Controls randomness. Higher is more expressive."
            )
            playback_rate_slider = gr.Slider(
                minimum=0.5, maximum=1.5, step=0.05, label="Playback Speed", value=params["playback_rate"],
                info="Directly adjusts playback speed. 1.0 is normal speed."
            )
        with gr.Row():
            exaggeration_slider = gr.Slider(
                minimum=0.0, maximum=1.5, step=0.05, label="Exaggeration", value=params["exaggeration"],
                info="Higher values can increase expressiveness and speech speed."
            )
            cfg_weight_slider = gr.Slider(
                minimum=0.0, maximum=1.0, step=0.05, label="CFG Weight", value=params["cfg_weight"],
                info="Lower values can improve pacing for fast speakers."
            )

        def update_and_save(key, value):
            params[key] = value
            save_settings()

        activate_checkbox.change(lambda x: update_and_save("activate", x), activate_checkbox, None)
        voice_dropdown.change(lambda x: update_and_save("selected_voice", x), voice_dropdown, None)
        temperature_slider.change(lambda x: update_and_save("temperature", x), temperature_slider, None)
        exaggeration_slider.change(lambda x: update_and_save("exaggeration", x), exaggeration_slider, None)
        cfg_weight_slider.change(lambda x: update_and_save("cfg_weight", x), cfg_weight_slider, None)
        playback_rate_slider.change(lambda x: update_and_save("playback_rate", x), playback_rate_slider, None)
        
        refresh_button.click(lambda: gr.Dropdown.update(choices=get_voice_files()), None, voice_dropdown)


def output_modifier(string, state, is_chat=False):
    if not params["activate"]:
        return string

    initialize_tts()
    if tts_model is None:
        return string

    # Hide any audio elements from a previous generation
    string = string.replace('<audio', '<!-- <audio').replace('</audio>', '</audio> -->')
    print("Chatterbox TTS: Generating audio...")

    try:
        output_dir = ensure_output_dir()
        timestamp = int(time.time())
        filename = f"chatterbox_output_{timestamp}.wav"
        output_path = str(output_dir / filename)

        text_for_tts = html.unescape(string).replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').replace(r"\x27", "'")

        gen_args = {
            "text": text_for_tts,
            "temperature": params["temperature"],
            "exaggeration": params["exaggeration"],
            "cfg_weight": params["cfg_weight"],
        }

        if params["selected_voice"] != "Default Voice":
            prompt_path = str(VOICES_DIR / params["selected_voice"])
            print(f"Chatterbox: Using voice '{params['selected_voice']}' with temp={params['temperature']}, exaggeration={params['exaggeration']}, cfg_weight={params['cfg_weight']}")
            gen_args["audio_prompt_path"] = prompt_path

        wav = tts_model.generate(**gen_args)
        sr = tts_model.sr

        torchaudio.save(output_path, wav, sr)

        print(f"Chatterbox TTS: Audio saved to {output_path}")

        # --- FINAL CORRECTED HTML BLOCK ---
        # This version uses an inline `onplay` event handler, which is the most robust method.
        # It completely removes the need for a separate <script> tag.
        playback_rate = params["playback_rate"]
        js_code = f"this.playbackRate = {playback_rate}; this.muted = false;"
        
        # We need to escape the double quotes inside the onplay attribute for valid HTML
        escaped_js_code = html.escape(js_code)

        audio_html = f'''
            <audio src="/file/{output_path.replace(chr(92), '/')}" autoplay muted onplay="{escaped_js_code}"></audio>
        '''
        string += audio_html

    except Exception:
        print("Error during Chatterbox TTS generation:")
        traceback.print_exc()
        return string.replace('<!-- <audio', '<audio').replace('</audio> -->', '</audio>')

    return string

# Load settings when the script is first loaded by the Web UI
load_settings()