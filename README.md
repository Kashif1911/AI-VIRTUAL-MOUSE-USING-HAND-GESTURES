# AI Virtual Mouse Using Hand Gesture

A Python-based hand-gesture control application for interacting with a computer through a webcam. The project uses MediaPipe hand landmarks, OpenCV, and PyAutoGUI, with additional controls and a Flask web dashboard.

> **License:** No license is included in this package. Do not describe the project as “license-free” or “copyright-free.” Add a license only after confirming that you have the right to distribute the project under its terms.

## Features

- Webcam-based hand tracking using MediaPipe and OpenCV
- Cursor movement with smoothing
- Left click: thumb + index-finger pinch
- Right click: thumb + middle-finger pinch
- Drag and drop: thumb + ring-finger pinch/hold
- Scrolling: thumbs-up to scroll up; thumbs-down to scroll down (other fingers folded)
- Volume control mode
- Brightness control mode
- Media control mode
- Offline voice commands using the bundled Vosk model
- Virtual drawing mode
- Browser/web dashboard and camera modes
- Account features in the web app, including registration/login and password-reset flow

Volume, brightness, media keys and voice use each system's native tools (see *What works where*). Test each feature on the target computer before demonstrating or submitting it.

## Project contents

- `main.py` — desktop application entry point
- `config.py` — application settings
- `modules/` — vision, gesture, cursor, mode, voice, volume, brightness, UI, and browser-frame modules
- `utils/` — helper functions
- `web/` — Flask dashboard, templates, static assets, and authentication database code
- `hand_landmarker.task` — bundled MediaPipe hand-landmarker model
- `models/vosk-model-small-en-us-0.15/` — bundled offline speech-recognition model
- `requirements.txt` — Python dependencies
- `run.py` (+ `run.bat`, `run.sh`) — cross-platform launcher: setup, models, start, doctor

## Quick start (Windows, macOS, Linux)

You only need **Python 3.9 – 3.12** and a webcam. One command does everything
(creates a private `.venv`, installs dependencies, downloads any missing model):

| System | Command |
|---|---|
| Any | `python run.py` |
| Windows | double-click `run.bat` |
| macOS / Linux | `./run.sh` |

Other commands:

```
python run.py web       # web dashboard (opens your browser)
python run.py setup     # install/update only
python run.py doctor    # check this computer and explain any problem
```

If your default Python is too new (e.g. 3.13), `run.py` automatically looks for
an installed 3.9–3.12 and uses that for the `.venv`.

The first run takes a few minutes (large packages). Later runs start instantly.

### What works where

| Feature | Windows | macOS | Linux |
|---|---|---|---|
| Cursor, clicks, drag, scroll | yes | yes | yes (X11) |
| Volume control | pycaw | built-in `osascript` | `pactl` or `amixer` |
| Brightness control | yes | needs `brew install brightness` | yes (or `brightnessctl`) |
| Media keys (play/next/prev) | yes | yes | yes (`playerctl` if installed) |
| Voice commands | yes | needs `brew install portaudio` | needs `sudo apt install portaudio19-dev python3-dev` |
| Web dashboard | yes | yes | yes |

Anything unavailable is skipped with a printed notice instead of crashing the app.

### Platform notes

- **macOS:** allow your Terminal / IDE under *System Settings → Privacy & Security* for **Camera, Microphone, Accessibility** and **Screen Recording**.
- **Linux:** cursor control needs an **X11/Xorg** session (Wayland blocks it). You may need `sudo apt install python3-tk python3-dev scrot` and your user in the `video` group.
- **Windows:** tick *Add python.exe to PATH* when installing Python.

### Manual install (optional)

```
python -m venv .venv
# Windows: .venv\Scripts\activate     macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

The `hand_landmarker.task` and Vosk model are bundled; if missing, `run.py` downloads them.

## Web dashboard

```
python run.py web
```

No configuration is required: a random secret key is generated once and stored
in `web/.secret_key` (never commit it). To override it, or to enable
password-reset email, set these environment variables:

- `AI_VM_SECRET_KEY` — your own secret key
- `AI_VM_EMAIL` / `AI_VM_EMAIL_APP_PASSWORD` — Gmail address and **app password** for reset emails
- `AI_VM_HOST` / `AI_VM_PORT` — default `127.0.0.1` / `5000`
- `AI_VM_CAMERA_INDEX` — use another webcam (default `0`)

The dashboard is a local development server; do not expose it to the internet.

## Gesture reference

| Gesture | Action |
|---|---|
| Move index fingertip | Move cursor |
| Thumb + index pinch | Left click |
| Thumb + middle pinch | Right click |
| Thumb + ring pinch/hold | Drag and drop |
| Thumb extended upward, other fingers folded | Scroll up |
| Thumb extended downward, other fingers folded | Scroll down |

Gesture detection can vary with camera angle, lighting, and hand orientation. Use the on-screen instructions and test the gestures before a demonstration.

## Troubleshooting

- **Camera not detected:** close other apps using the webcam and check `config.py` for the camera index.
- **Anything not working:** run `python run.py doctor`, then `python run.py setup --force`.
- **Model error:** verify that `hand_landmarker.task` is in the project root and the Vosk model directory is present under `models/`.
- **Password reset email does not send:** confirm all three environment variables above are configured and the Gmail app password is valid.
- **Volume/brightness not changing:** desktop monitors without DDC/CI support cannot change brightness from software; see the platform table above.
- **Voice disabled:** PyAudio needs system audio libraries (see the table above); the rest of the app works without it.

## Tests

The repository includes individual scripts such as `test_brightness.py`, `test_voice.py`, `test_volume.py`, and a database test under `web/auth/`. These are component checks, not a complete automated test suite. Run them only when ready for the relevant hardware interaction; some tests may change volume, brightness, or trigger desktop actions.

## Acknowledgements

- MediaPipe for hand landmark detection
- OpenCV for webcam processing
- PyAutoGUI for desktop input control
- Vosk for offline speech recognition
# AI-VIRTUAL-MOUSE-USING-HAND-GESTURES
# AI-VIRTUAL-MOUSE-USING-HAND-GESTURES
# AI-VIRTUAL-MOUSE-USING-HAND-GESTURES
