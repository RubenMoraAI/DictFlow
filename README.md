# DictFlow
App that transcribes audio to text (voice dictation) using the Google Gemini API and formats the result. A free, open-source voice dictation tool.

# DictFlow: Audio Transcription and Enhancement Tool

DictFlow is a Python-based desktop application designed to efficiently convert audio files to text and subsequently enhance the transcribed text for improved readability and coherence.

## 🚀 Key Features

*   **Single-pass refinement pipeline:** transcribes your voice and, in the *same* Gemini call, removes fillers/hesitations/repetitions, fixes punctuation and obvious dictation grammar — without inventing content.
*   **Context-aware styling (UI Automation):** DictFlow detects the **focused application** when you dictate and adapts the output style automatically:
    *   **Slack / WhatsApp / Discord** → direct, agile tone with smart line breaks.
    *   **Gmail / Outlook / mail** → formal structure with greeting and closing.
    *   **VS Code / Cursor** → treated as code/comments; precise technical terms and `camelCase`/`snake_case`.
    *   **Notion / notes** → bullets, numbered lists and bold for task lists or brainstorms.
*   **Shortcuts & text expansion:** define `trigger = expansion` snippets that are substituted exactly — e.g. `ASAP → as soon as possible`, or `mi dirección → <your saved address>`. Great for forcing English output on specific phrases.
*   **Output language control:** keep it automatic, or force the final text to **Spanish** or **English** (also via the voice commands "en inglés" / "in English").
*   **Transcription History & Usage Statistics:** keeps a record of transcriptions and tracks usage.

## 🛠️ How to Use

Video Tutorial: https://www.youtube.com/watch?v=vwsnipfGLms

There are two ways to use this tool: by running the Python script directly or by using the executable file.

### Option 1: Run the Python Script Code (For Developers)

This option provides more flexibility if you want to modify the code.

**Prerequisites:**
*   Python 3 installed on your system.
*   `pip` (Python's package manager) installed.

**Steps:**
1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    ```
2.  **Navigate to the project directory:**
    
3.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv .venv
    ```
4.  **Activate the virtual environment:**
    *   On Windows:
        ```bash
        .venv\Scripts\activate
        ```
    *   On macOS/Linux:
        ```bash
        source .venv/bin/activate
        ```
5.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
6.  **Set up your Gemini API key:**
    The recommended way is to launch the app and paste your key in
    **Configuración** → **API** (right-click the floating window). The key is
    stored securely in your operating system's keyring (Windows Credential
    Manager / macOS Keychain / Linux Secret Service) — never in plain text.
    Get a key at https://aistudio.google.com/app/apikey.

    *(Optional, for automation: copy `.env.example` to `.env` and set
    `GEMINI_API_KEY=your_key_here`. On the next startup it is imported into the
    keyring.)*
7.  **Run the application:**
    ```bash
    python mainsoft.py
    ```

### Option 2: Use the Executable File (The Easiest Way)

If you just want to use the application without dealing with Python installations or dependencies, this is your best option.

1.  Download `DictFlow.exe` from the project's Releases page.
2.  Double-click it to launch the application — a small vertical bar appears.
3.  Right-click the bar → **Configuración** → **API**, paste your Gemini API key
    (get one free at https://aistudio.google.com/app/apikey) and click *Guardar*.
    The key is stored securely in Windows Credential Manager. That's it!

> The `.exe` is fully self-contained (Python and all dependencies are bundled),
> so it runs on any Windows 10/11 machine without installing anything.

### Option 3: Build the Executable Yourself

If you cloned the repo (Option 1) you can produce your own `DictFlow.exe`:

```powershell
.\build_exe.ps1
```

This installs [PyInstaller](https://pyinstaller.org) and bundles everything into
a single file at `dist\DictFlow.exe`. (Under the hood it runs
`pyinstaller --onefile --windowed --name DictFlow --collect-all customtkinter
--collect-all sounddevice --collect-all keyring mainsoft.py`.) The window/app icon
comes from `dictflow.ico`, which you can regenerate with `python generate_icon.py`.

### Start Automatically with Windows

To have DictFlow launch every time you log in:

```powershell
.\install.ps1
```

This copies the executable to `%LOCALAPPDATA%\DictFlow` and adds a shortcut to your
Startup folder. To turn it off, run `.\install.ps1 -Remove` (or disable *DictFlow*
under **Task Manager → Startup apps**).

## 🎹 Using the App (Controls)

Once running (via `python mainsoft.py` or the executable), a small floating bar
appears at the bottom-center of your screen. From there:

*   **Start / stop recording:** press **`Ctrl + Shift + Q`** (the default hotkey, configurable in **Configuración → Atajos**).
    Press it once to start recording your voice and again to stop. The
    transcribed text is pasted automatically into whatever window is focused.
*   **Text enhancement:** toggle the checkbox on the bar to enable/disable
    automatic punctuation and formatting (done in the same Gemini call).
*   **Settings:** right-click the bar and choose **Configuración** to set your
    API key, edit the enhancement prompt, pick the Gemini model, or view the
    history and usage statistics.
*   **Move the bar:** left-click and drag it anywhere on the screen.
*   **Quit:** right-click the bar and choose **Salir**.

> **Note:** you must set a valid Gemini API key before recording (see step 6
> above). The app will warn you if it is missing.

## 🧠 Smart Pipeline, Context & Shortcuts

DictFlow runs everything in **one Gemini call** for the lowest possible latency:

1.  **STT clean-up** — removes fillers ("ehhh", "o sea", "este", "mmm"), hesitations and stutter repetitions.
2.  **Natural punctuation & grammar** — adds punctuation and fixes obvious spoken-dictation mistakes while preserving your vocabulary and message.
3.  **Context adaptation** — the focused app is detected automatically (see [context_detector.py](context_detector.py)) and the style is adjusted (Slack/WhatsApp, Gmail/mail, VS Code/Cursor, Notion/notes).
4.  **Shortcut expansion** — your `trigger = expansion` snippets are substituted exactly.

### Configuring shortcuts and output language

Right-click the bar → **Configuración** → **Atajos** tab. Enter one shortcut per line:

```
ASAP = as soon as possible
FYI = for your information
mi dirección = Calle Falsa 123, Springfield
```

When you dictate a trigger, it is replaced verbatim by its expansion (so an English
expansion stays in English even if you dictated in Spanish). In the same tab you can
set the **output language** to *Automatic*, *Spanish* or *English*. You can also switch
language on the fly by starting your dictation with "en inglés" / "in English".

The same **Atajos** tab lets you change the **recording hotkey** (type a combo such as
`ctrl+shift+q`, `pause` or `f9` and press *Cambiar*).

> The **Master Prompt** that drives this whole pipeline is fully editable in
> **Configuración** → **Configuración** tab, so you can tweak the rules to your taste.
>
> If a transcription fails (e.g. no API quota), DictFlow shows a brief on-screen
> notice instead of pasting an error into your document.

## 📂 Project File Structure

Here is a description of the most important files and their functions:

### Core Files (The heart of the software)

*   `mainsoft.py`: The application's entry point. Run this file to start the program.
*   `text_enhancer.py`: Contains all the logic for processing and enhancing the transcribed text (adding punctuation, capitalization, etc.).
*   `transcription_history.py`: Manages the transcription history by saving and retrieving data.
*   `context_detector.py`: Detects the focused application (Windows UI Automation) so the pipeline can adapt the output style.

### Secondary and Generated Files

*   `requirements.txt`: List of Python dependencies installed with `pip install -r requirements.txt`.
*   `.env.example` / `.env`: Optional local environment variables. The Gemini API key is stored in the OS keyring, **not** here. `.env` is never committed (see `.gitignore`).
*   `.gitignore`: Prevents secrets and generated files from being pushed to GitHub.
*   `cspell.json` / `package.json`: Spell-checking configuration (see below).
*   `config.json`: Configuration file (master prompt, model, enhancement toggle, shortcuts, output language). The API key is **not** stored here — it lives in the OS keyring.
*   `transcription_history.json`: A JSON-format database where the history of all transcriptions is stored.
*   `usage_statistics.json`: A JSON file that saves data on how the application is used.
*   `logs/dictflow.log`: A log file that records information about events or errors that may occur during execution.
*   `build_exe.ps1`: Script that builds the standalone `DictFlow.exe` (see Option 3).
*   `install.ps1`: Installs the exe and enables auto-start on Windows login.
*   `generate_icon.py` / `dictflow.ico`: Generates and stores the app icon.
*   `dist/`: The folder where the built **executable file (`DictFlow.exe`)** is placed.
*   `.venv/`: The folder for the Python virtual environment (if created).

## ✅ Spell Checking (cspell)

The project ships with a [cspell](https://cspell.org) configuration for English and Spanish.

*   **In VS Code:** install the *Code Spell Checker* extension; it picks up `cspell.json` automatically.
*   **From the command line** (requires Node.js):
    ```bash
    npm install
    npm run spell
    ```
    Add project-specific terms to the `words` list in `cspell.json` to silence false positives.
