# Chatterbox TTS for text-generation-webui

This extension integrates the high-quality, realistic [Chatterbox TTS model](https://github.com/resemble-ai/chatterbox) by Resemble AI directly into the text-generation-webui. It automatically converts the AI's generated text responses into speech and plays them in your browser.

## Features

*   **Automatic Playback**: AI responses are automatically spoken as they are generated.
*   **High-Quality Voice**: Utilizes the powerful Chatterbox model for natural and expressive speech.
*   **Custom Voice Cloning**: Use your own `.wav` or `.mp3` files to clone a voice for TTS generation.
*   **Fine-Grained Control**: Adjust parameters like Temperature, Exaggeration, CFG Weight, and Playback Speed to customize the voice output.
*   **GPU Acceleration**: Automatically uses your CUDA-enabled GPU for fast inference if available.
*   **Persistent Settings**: Your chosen settings are saved and loaded automatically.

## Installation

Follow these steps to install the extension. The most common point of failure is a mismatch between PyTorch and CUDA versions, so a detailed troubleshooting guide is included below.

### Step 1: Add the Extension

Place the `chatterbox_tts` folder into the `extensions` directory of your text-generation-webui installation.

### Step 2: Install Dependencies (The Standard Way)

1.  Open a command line/terminal and navigate to your text-generation-webui root folder.
2.  Activate the correct Python environment. For portable/one-click installs on Windows, you'll use the included Python executable.
3.  Run the following command to install the required libraries:

    **For Windows (Portable/One-Click):**
    ```bash
    .\portable_env\python.exe -m pip install -r .\extensions\chatterbox_tts\requirements.txt
    ```

    **For other systems (Conda, venv, etc.):**
    *(Ensure your virtual environment is activated first)*
    ```bash
    pip install -r extensions/chatterbox_tts/requirements.txt
    ```

4.  Start the web UI. If everything works, you are done! If you encounter errors, especially CUDA-related ones, proceed to the troubleshooting section.

## Installation Troubleshooting: PyTorch & CUDA Mismatch

**This is the most common issue.** The `chatterbox` library requires a specific version of PyTorch. The `requirements.txt` file might install a version of PyTorch that does not match the CUDA version your system (and the web UI) is configured to use. This can lead to errors or the model falling back to the much slower CPU.

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
    If you are using **CUDA 11.8**, you would change `cu121` to `cu118`:
    ```bash
    .\portable_env\python.exe -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
    ```
    **Adjust the command to match your environment.**

### Diagnostic Scripts

This extension includes two diagnostic scripts to help you verify your environment. Run them from your web UI's root folder:

*   **Check CUDA and Torch:**
    This script tells you if PyTorch can see your GPU.
    ```bash
    .\portable_env\python.exe .\extensions\chatterbox_tts\diagCuda.py
    ```

*   **Check Chatterbox Installation:**
    This script attempts to load the Chatterbox model.
    ```bash
    .\portable_env\python.exe .\extensions\chatterbox_tts\diagChatter.py
    ```

Share the output of these scripts if you need to ask for help resolving issues.

## How to Use

1.  Start or restart the text-generation-webui.
2.  Navigate to the **Session** tab.
3.  You will find a new accordion section named **Chatterbox TTS**.
4.  Check the **Activate Chatterbox TTS** box to enable speech generation.
5.  All subsequent AI messages will be converted to audio and played automatically.

## Parameters Explained

### Main Settings
*   **Activate Chatterbox TTS**: The main switch to turn the extension on or off.
*   **Custom Voice**: Select a voice to use for generation. `Default Voice` uses the standard Chatterbox voice. Other options are populated from your `voices` folder.
*   **Refresh Voices**: Click this button to rescan the `voices` folder for new audio files.

### Advanced Voice Settings
*   **Temperature** (Default: 0.7): Controls the randomness and expressiveness of the speech. Higher values lead to more varied and potentially more emotional speech, while lower values are more consistent and monotonic.
*   **Playback Speed** (Default: 1.0): Adjusts the playback speed of the final audio clip. `1.0` is normal speed, `<1.0` is slower, and `>1.0` is faster. This does not affect the voice generation itself, only the playback.
*   **Exaggeration** (Default: 0.5): Influences the expressiveness and can also affect the pace of the speech. Higher values can make the voice more dynamic.
*   **CFG Weight** (Default: 0.5): Classifier-Free Guidance weight. Lowering this value can sometimes improve the pacing and naturalness for voices that tend to speak very quickly.

## Using Custom Voices

You can clone any voice by providing a short audio sample.

1.  Get a clean audio recording of the target voice. The best samples are high-quality `.wav` or `.mp3` files with a single speaker and minimal background noise.
2.  Place your audio file(s) into the `text-generation-webui/extensions/chatterbox_tts/voices/` directory.
3.  In the web UI, click the **Refresh Voices** button.
4.  Your audio file will now be available as an option in the **Custom Voice** dropdown menu. Select it to generate speech in that voice.