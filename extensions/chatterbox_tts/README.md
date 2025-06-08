# Chatterbox TTS for text-generation-webui

This extension integrates the high-quality, realistic [Chatterbox TTS model](https://github.com/resemble-ai/chatterbox) by Resemble AI directly into the text-generation-webui.

It offers two modes of operation:
1.  **Standard TTS**: Automatically converts the AI's generated text responses into speech.
2.  **Conversational Mode**: Enables a hands-free, voice-to-voice conversation with the AI using your microphone.

## Features

*   **Automatic Playback**: AI responses are automatically spoken as they are generated.
*   **Conversational Mode**: Engage in a hands-free conversation. Your spoken words are transcribed by Whisper, sent to the AI, and the AI's response is spoken back to you.
*   **High-Quality Voice**: Utilizes the powerful Chatterbox model for natural and expressive speech.
*   **Custom Voice Cloning**: Use your own `.wav` or `.mp3` files to clone a voice for TTS generation.
*   **Per-Character Settings**: Automatically save and load voice settings for each character you chat with.
*   **Fine-Grained Control**: Adjust Temperature, Exaggeration, CFG Weight, and Playback Speed to customize the voice output.
*   **GPU Acceleration**: Automatically uses your CUDA-enabled GPU for fast inference if available.
*   **Persistent Settings**: Your chosen settings are saved and loaded automatically.

## Installation

Follow these steps to install the extension. The new Conversational Mode requires additional dependencies, including `ffmpeg` and OpenAI's `whisper`.

### Step 1: Install `ffmpeg` (Required for Conversational Mode)

The `whisper` model, used for speech-to-text, requires `ffmpeg` to be installed on your system.

*   **Windows**:
    1.  Download a release from [ffmpeg.org](https://ffmpeg.org/download.html).
    2.  Extract the archive.
    3.  Add the `bin` directory from the extracted folder to your system's PATH.
    4.  You can verify the installation by opening a new terminal and running `ffmpeg -version`.

*   **macOS**:
    ```bash
    brew install ffmpeg
    ```

*   **Linux (Debian/Ubuntu)**:
    ```bash
    sudo apt update && sudo apt install ffmpeg
    ```

### Step 2: Install Python Dependencies

1.  Place the `chatterbox_tts` folder into the `extensions` directory of your text-generation-webui installation.
2.  Open a command line/terminal and navigate to your text-generation-webui root folder.
3.  Activate your Python environment (e.g., `conda activate` or the `cmd_...bat` script for one-click installs).
4.  Run the following command to install all required libraries from the included `requirements.txt`:

    **For Windows (Portable/One-Click):**
    ```bash
    .\portable_env\python.exe -m pip install -r .\extensions\chatterbox_tts\requirements.txt
    ```

    **For other systems (Conda, venv, etc.):**
    *(Ensure your virtual environment is activated first)*
    ```bash
    pip install -r extensions/chatterbox_tts/requirements.txt
    ```

    > **Note:** The `requirements.txt` should include `chatterbox-tts`, `openai-whisper`, `sounddevice`, `soundfile`, and `scipy`.

5.  Start the web UI. If you encounter errors, especially CUDA-related ones, proceed to the troubleshooting section.

## Installation Troubleshooting: PyTorch & CUDA Mismatch

**This is the most common issue.** The `chatterbox` and `whisper` libraries require a version of PyTorch that matches the CUDA version your system (and the web UI) is configured to use. This is crucial for both TTS and speech-to-text to work on the GPU.

### How to Fix It

The solution is to manually uninstall the incorrect PyTorch version and reinstall one that explicitly matches your CUDA version.

1.  **Uninstall the existing PyTorch:**
    *(Use the same python executable as in Step 2 above)*
    ```bash
    .\portable_env\python.exe -m pip uninstall torch torchvision torchaudio
    ```

2.  **Reinstall PyTorch with the correct CUDA version:**
    Go to the [PyTorch "Get Started" page](https://pytorch.org/get-started/locally/) to find the correct command for your system.

    For example, if your web UI is running on **CUDA 12.1**, the command would be:
    ```bash
    .\portable_env\python.exe -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
    ```
    If you are using **CUDA 11.8**, you would change `cu121` to `cu118`. **Adjust the command to match your environment.**

### Diagnostic Scripts

This extension includes two diagnostic scripts to help you verify your environment. Run them from your web UI's root folder:

*   **Check CUDA and Torch:** `.\portable_env\python.exe .\extensions\chatterbox_tts\diagCuda.py`
*   **Check Chatterbox Installation:** `.\portable_env\python.exe .\extensions\chatterbox_tts\diagChatter.py`

## How to Use

### Standard TTS Mode

This mode simply speaks the AI's responses aloud.

1.  Start or restart the text-generation-webui.
2.  Navigate to the **Session** tab.
3.  You will find a new accordion section named **Chatterbox TTS**.
4.  Check the **Activate Chatterbox TTS** box.
5.  All subsequent AI messages will be converted to audio and played automatically.

### Conversational Mode

This mode allows for a full voice-to-voice conversation.

1.  **First-time Setup**: In the **Chatterbox TTS** section, check the box labeled **Enable Conversational Mode**.
2.  **IMPORTANT**: You **must restart** the text-generation-webui after checking this box. This allows the extension to load the Whisper speech-to-text model on startup.
3.  Once reloaded, click the **Start Conversation** button.
4.  The **Status** display will change to "Listening...".
5.  Speak your prompt into your microphone. The extension will automatically detect when you've finished speaking.
6.  The status will update as it transcribes your speech, sends it to the AI, and generates the audio response.
7.  The AI's response will be played back through your speakers. The loop then repeats, returning to the "Listening..." state.
8.  Click the **Stop Conversation** button at any time to end the session.

## Parameters Explained

### Main Settings
*   **Activate Chatterbox TTS**: The main switch to turn the extension on or off for standard TTS playback.

### Conversational Mode
*   **Enable Conversational Mode**: A one-time setup toggle. Must be checked (and the UI restarted) to enable the hands-free conversational feature. This pre-loads the necessary models.
*   **Status**: A non-interactive display showing the current state of the conversation manager (e.g., Idle, Listening..., Generating...).
*   **Start/Stop Conversation**: Buttons to begin and end the hands-free conversational loop.

### Voice Settings
*(These settings are automatically saved and loaded for the currently selected character.)*

*   **Voice**: Select a voice for generation. `Default Voice` uses the standard Chatterbox voice. Other options are populated from your `voices` folder.
*   **Refresh Voices**: Rescans the `voices` folder for new audio files.
*   **Temperature** (Default: 0.7): Controls the randomness of the speech. Higher values lead to more varied and emotional speech.
*   **Playback Speed** (Default: 1.0): Adjusts the playback speed of the final audio clip. `<1.0` is slower, `>1.0` is faster.
*   **Exaggeration** (Default: 0.5): Influences the expressiveness and pace of the speech.
*   **CFG Weight** (Default: 0.5): Classifier-Free Guidance weight. Lowering this can sometimes improve pacing for voices that speak too quickly.
*   **Save Settings for Character**: Manually save the current voice settings for the active character.

## Using Custom Voices

You can clone any voice by providing a short audio sample.

1.  Get a clean audio recording of the target voice. The best samples are high-quality `.wav` or `.mp3` files with a single speaker and minimal background noise.
2.  Place your audio file(s) into the `text-generation-webui/extensions/chatterbox_tts/voices/` directory.
3.  In the web UI, click the **Refresh Voices** button.
4.  Your audio file will now be available in the **Voice** dropdown. Select it to generate speech in that voice. When you save, it will be linked to the current character.