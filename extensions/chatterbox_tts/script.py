import gradio as gr
import chatterbox
import time
from pathlib import Path
import traceback
import torch
import torchaudio
import html
import json
import numpy as np
import sounddevice as sd
import soundfile as sf
import threading
import queue
import whisper
from scipy.io.wavfile import write

# --- Global State and Communication ---
APP_STATE = { "manager_thread": None, "tts_request_queue": queue.Queue(), "whisper_model": None, "tts_model": None }

# --- Conversational Mode Logic (Unchanged) ---
class ConversationManager(threading.Thread):
    def __init__(self, status_q, text_q, tts_q):
        super().__init__()
        self.running = False; self.status_queue = status_q; self.text_queue = text_q; self.tts_request_queue = tts_q; self.daemon = True
    def _update_status(self, text): print(f"Chatterbox Manager: {text}"); self.status_queue.put(text)
    def stop(self): self._update_status("Stopping..."); self.running = False; self.tts_request_queue.put(None)
    def run(self):
        self.running = True; self._update_status("Manager thread started.")
        while self.running:
            self._update_status("Listening..."); user_text = self._record_and_transcribe_loop()
            if not self.running: break
            if user_text:
                self._update_status(f"Submitting user text..."); self.text_queue.put(user_text)
                self._update_status("Waiting for AI response..."); text_to_speak = self.tts_request_queue.get()
                if text_to_speak is None or not self.running: break
                self._update_status("Generating and playing audio..."); generate_and_play_audio(text_to_speak)
                self._update_status("Playback finished.")
            elif self.running: self._update_status("No speech detected, listening again..."); time.sleep(0.5)
        self._update_status("Idle")
    def _record_and_transcribe_loop(self):
        audio_queue = queue.Queue(); stop_recording_event = threading.Event()
        def _record_audio_thread(audio_q, stop_event):
            def callback(indata, frames, time, status):
                if status: print(status)
                audio_q.put(bytes(indata))
            try:
                with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16', channels=1, callback=callback):
                    while not stop_event.is_set() and self.running: time.sleep(0.1)
            except Exception as e: self._update_status(f"Audio Error: {e}")
        recording_thread = threading.Thread(target=_record_audio_thread, args=(audio_queue, stop_recording_event)); recording_thread.start()
        recorded_audio, silence_start_time, has_speech_started = [], None, False
        while self.running:
            try:
                audio_chunk = np.frombuffer(audio_queue.get(timeout=1.0), dtype=np.int16)
                is_silent = np.abs(audio_chunk).mean() < 300
                if not is_silent:
                    if not has_speech_started: has_speech_started = True
                    recorded_audio.append(audio_chunk); silence_start_time = None
                elif has_speech_started:
                    recorded_audio.append(audio_chunk)
                    if silence_start_time is None: silence_start_time = time.time()
                    elif time.time() - silence_start_time > 1.2: break
            except queue.Empty:
                if has_speech_started: break
        stop_recording_event.set(); recording_thread.join()
        if not self.running or not recorded_audio: return ""
        full_recording, temp_filepath = np.concatenate(recorded_audio), str(TEMP_DIR / "user_speech.wav")
        write(temp_filepath, 16000, full_recording)
        if APP_STATE.get('whisper_model'):
            result = APP_STATE['whisper_model'].transcribe(temp_filepath, fp16=torch.cuda.is_available())
            return result['text'].strip()
        self._update_status("Whisper model not loaded!"); return ""

# --- Gradio UI and Functions ---
def ui():
    status_q, text_q, tts_q = queue.Queue(), queue.Queue(), APP_STATE["tts_request_queue"]
    
    with gr.Accordion("Chatterbox TTS", open=True):
        # 1. Define all UI components first
        with gr.Row(): activate_checkbox = gr.Checkbox(value=params["activate"], label="Activate Chatterbox TTS ")
        gr.Markdown("---")
        gr.Markdown("### Conversational Mode ")
        with gr.Row(): activate_conversational_checkbox = gr.Checkbox(value=params["activate_conversational_mode"], label="Enable Conversational Mode (requires TextGen restart)")
        status_display = gr.Textbox(label="Status", value="Idle", interactive=False)
        with gr.Row(): start_button = gr.Button("Start Conversation"); stop_button = gr.Button("Stop Conversation")
        gr.Markdown("---")
        gr.Markdown("### Voice Settings")
        gr.Markdown("*(Settings are loaded when you select a character. Use the button below to save.)*")
        with gr.Row(): voice_dropdown = gr.Dropdown(label="Voice", choices=get_voice_files(), value=params["selected_voice"]); refresh_button = gr.Button("Refresh Voices")
        with gr.Row(): temperature_slider = gr.Slider(minimum=0.1, maximum=1.0, step=0.05, label="Temperature", value=params["temperature"]); playback_rate_slider = gr.Slider(minimum=0.5, maximum=1.5, step=0.05, label="Playback Speed", value=params["playback_rate"])
        with gr.Row(): exaggeration_slider = gr.Slider(minimum=0.0, maximum=1.5, step=0.05, label="Exaggeration", value=params["exaggeration"]); cfg_weight_slider = gr.Slider(minimum=0.0, maximum=1.0, step=0.05, label="CFG Weight", value=params["cfg_weight"])
        with gr.Row(): save_character_button = gr.Button("Save Settings for Character")
        gr.Markdown("More info on settings be found at [Resemble AI's Chatterbox](https://github.com/resemble-ai/chatterbox).")

        voice_setting_components = [voice_dropdown, temperature_slider, playback_rate_slider, exaggeration_slider, cfg_weight_slider]
        
        # This is now our primary communication bridge from JS to Python
        character_name_poller = gr.Textbox(visible=False, elem_id="chatterbox_character_name_poller")

        prompt_injector = gr.Textbox(visible=False, elem_id="chatterbox_prompt_injector")
        status_poller = gr.Textbox(visible=False)

        # 2. Define all handler functions
        def load_character_settings(character_name):
            """This function is ONLY triggered by the poller textbox's .change() event."""
            if not character_name or character_name == "None":
                return gr.update(value="Save Settings for Character"), gr.update(), gr.update(), gr.update(), gr.update(), gr.update()
            
            # This log should now show the correct character name.
            print(f"Chatterbox: LOAD triggered for character: '{character_name}'")
            
            char_settings = params["character_settings"].get(character_name, {
                "selected_voice": params["selected_voice"], "temperature": params["temperature"],
                "playback_rate": params["playback_rate"], "exaggeration": params["exaggeration"],
                "cfg_weight": params["cfg_weight"]
            })
            for key in SETTINGS_KEYS: params[key] = char_settings.get(key, params.get(key))
            return (
                gr.update(value=f"Save Settings for '{character_name}'"),
                gr.update(value=char_settings.get("selected_voice")), gr.update(value=char_settings.get("temperature")),
                gr.update(value=char_settings.get("playback_rate")), gr.update(value=char_settings.get("exaggeration")),
                gr.update(value=char_settings.get("cfg_weight"))
            )

        def save_character_settings(character_name, voice, temp, speed, exag, cfg):
            """This function is ONLY triggered by the new visible 'Save' button."""
            params.update({"selected_voice": voice, "temperature": temp, "playback_rate": speed, "exaggeration": exag, "cfg_weight": cfg})
            if not character_name or character_name == "None":
                print("Chatterbox: No character selected to save settings for.")
                return
            print(f"Chatterbox: SAVE triggered for character '{character_name}'.")
            new_settings = {"selected_voice": voice, "temperature": temp, "playback_rate": speed, "exaggeration": exag, "cfg_weight": cfg}
            params["character_settings"][character_name] = new_settings
            save_settings()
            print("Chatterbox: Settings file updated successfully.")

        def start_conversation_handler():
            # ... (unchanged)
            if not params.get("activate_conversational_mode", False) or not APP_STATE.get('whisper_model'):
                status_q.put("Conversational mode is not enabled. Check the box and reload UI.")
                return f"Error... {time.time()}"
            if APP_STATE.get("manager_thread") and APP_STATE["manager_thread"].is_alive(): return "Already running."
            manager = ConversationManager(status_q, text_q, tts_q); APP_STATE["manager_thread"] = manager; manager.start()
            return f"Starting... {time.time()}"

        def stop_conversation_handler():
            # ... (unchanged)
            if APP_STATE.get("manager_thread") and APP_STATE["manager_thread"].is_alive(): APP_STATE["manager_thread"].stop()
            return "Stopping..."

        def poll_for_updates():
            # ... (unchanged)
            status_update, text_update = None, None
            try: status_update = status_q.get_nowait();
            except queue.Empty: pass
            try: text_update = text_q.get_nowait()
            except queue.Empty: pass
            return gr.update(value=status_update) if status_update else gr.update(), gr.update(value=text_update) if text_update else gr.update()

        # 3. Wire all the events together
        character_name_poller.change(fn=load_character_settings, inputs=[character_name_poller], outputs=[save_character_button] + voice_setting_components)
        save_character_button.click(fn=save_character_settings, inputs=[character_name_poller] + voice_setting_components, outputs=None)
        
        start_button.click(start_conversation_handler, None, [status_poller])
        stop_button.click(stop_conversation_handler, None, [status_display])
        status_poller.change(poll_for_updates, None, [status_display, prompt_injector], every=0.2)
        prompt_injector.change(None, prompt_injector, None, _js="""(t) => { if (!t) return; setTimeout(() => { const i = document.querySelector('textarea[placeholder=\"Send a message\"]'); if (i) { i.value = t; i.dispatchEvent(new Event('input', { bubbles: true })); const b = document.getElementById('Generate'); if (b) b.click(); } }, 100); }""")
        activate_checkbox.change(lambda x: update_and_save("activate", x), activate_checkbox, None)
        activate_conversational_checkbox.change(lambda x: update_and_save("activate_conversational_mode", x), activate_conversational_checkbox, None)
        refresh_button.click(lambda: gr.Dropdown.update(choices=get_voice_files()), None, voice_dropdown)
        
        # 4. Define the JS injector as the very last element
        gr.HTML("""<img src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7" style="display:none" onload="(()=>{console.log('Chatterbox JS initialised.');let currentVal='';function c(){let e=document.querySelector('input[aria-label=\\'Character\\']'),t=document.querySelector('#chatterbox_character_name_poller textarea');if(e&&t&&e.value!==currentVal){currentVal=e.value;console.log(`Chatterbox JS: Detected character change to: ${currentVal}. Triggering Python.`);t.value=currentVal;t.dispatchEvent(new Event('input',{bubbles:true}))}}setInterval(c,500)})();"/>""")

# --- Core Logic & Setup (Unchanged) ---
def output_modifier(string, state, is_chat=False):
    is_conv_mode_active = APP_STATE.get("manager_thread") and APP_STATE["manager_thread"].is_alive()
    is_tts_active = params.get("activate", False)
    if not is_tts_active: return string
    if is_conv_mode_active: APP_STATE["tts_request_queue"].put(string)
    else: generate_and_play_audio(string)
    return string
def generate_and_play_audio(text):
    audio_path = generate_tts_audio_file(text)
    if audio_path:
        try: data, fs = sf.read(audio_path, dtype='float32'); sd.play(data, int(fs * params['playback_rate'])); sd.wait()
        except Exception as e: print(f"Chatterbox: Error playing audio file: {e}")
def generate_tts_audio_file(text_to_speak):
    if not initialize_tts(): return None
    tts_model = APP_STATE.get("tts_model")
    if not tts_model: return None
    output_dir, timestamp = EXTENSION_DIR / "outputs", int(time.time() * 1000)
    output_path = str(output_dir / f"chatterbox_output_{timestamp}.wav")
    text_to_speak = html.unescape(text_to_speak).replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').replace(r"\x27", "'")
    gen_args = { "text": text_to_speak, "temperature": params["temperature"], "exaggeration": params["exaggeration"], "cfg_weight": params["cfg_weight"] }
    if params["selected_voice"] != "Default Voice": gen_args["audio_prompt_path"] = str(VOICES_DIR / params["selected_voice"])
    try: wav = tts_model.generate(**gen_args); torchaudio.save(output_path, wav, tts_model.sr); return output_path
    except Exception as e: print(f"Chatterbox: FATAL ERROR during TTS generation: {e}"); return None

SETTINGS_KEYS = ["selected_voice", "temperature", "playback_rate", "exaggeration", "cfg_weight"]
params = { "activate": False, "activate_conversational_mode": False, "selected_voice": "Default Voice", "temperature": 0.7, "exaggeration": 0.5, "cfg_weight": 0.5, "playback_rate": 1.0, "character_settings": {} }
EXTENSION_DIR, VOICES_DIR = Path("extensions/chatterbox_tts"), Path("extensions/chatterbox_tts/voices")
SETTINGS_FILE, TEMP_DIR = EXTENSION_DIR / "settings.json", EXTENSION_DIR / "temp"

def ensure_dirs(): VOICES_DIR.mkdir(parents=True, exist_ok=True); (EXTENSION_DIR / "outputs").mkdir(parents=True, exist_ok=True); TEMP_DIR.mkdir(parents=True, exist_ok=True)
def get_voice_files(): return ["Default Voice"] + [p.name for p in VOICES_DIR.glob("*") if p.suffix in (".wav", ".mp3")]
def save_settings():
    with open(SETTINGS_FILE, 'w') as f: json.dump(params, f, indent=4)
def load_settings():
    if not SETTINGS_FILE.exists(): return
    try:
        with open(SETTINGS_FILE, 'r') as f: loaded_params = json.load(f)
        migrated = False
        if "character_voices" in loaded_params and isinstance(loaded_params["character_voices"], dict):
            print("Chatterbox: Found old 'character_voices' key. Migrating to 'character_settings'.")
            if "character_settings" not in loaded_params: loaded_params["character_settings"] = {}
            for char, voice in loaded_params["character_voices"].items():
                if char not in loaded_params["character_settings"]: loaded_params["character_settings"][char] = {"selected_voice": voice}
            del loaded_params["character_voices"]; migrated = True
        if "character_settings" not in loaded_params: loaded_params["character_settings"] = {}
        params.update(loaded_params)
        if migrated: print("Chatterbox: Migration complete. Saving corrected settings file."); save_settings()
    except Exception as e: print(f"Chatterbox: Could not load or migrate settings: {e}")
def update_and_save(key, value): params[key] = value; save_settings()
def initialize_tts():
    if APP_STATE.get("tts_model") is not None: return True
    print("Chatterbox: Initializing Chatterbox TTS model...")
    try:
        device = "cuda" if torch.cuda.is_available() else "cpu"; model = chatterbox.ChatterboxTTS.from_pretrained(device=device); APP_STATE["tts_model"] = model; print("Chatterbox: TTS model initialized successfully."); return True
    except Exception as e: APP_STATE["tts_model"] = None; print(f"Chatterbox: FATAL ERROR initializing TTS model: {e}"); return False
def initial_setup():
    print("Chatterbox: Performing initial setup...")
    ensure_dirs(); load_settings()
    if params.get("activate_conversational_mode", False):
        try:
            print("Chatterbox: Conversational mode enabled, loading Whisper STT model..."); APP_STATE['whisper_model'] = whisper.load_model("base.en"); print("Chatterbox: Whisper STT model loaded.")
        except Exception as e: APP_STATE['whisper_model'] = None; print(f"Chatterbox: FATAL - Could not load Whisper model: {e}")
    else: print("Chatterbox: Conversational mode disabled. Skipping Whisper model load.")

initial_setup()