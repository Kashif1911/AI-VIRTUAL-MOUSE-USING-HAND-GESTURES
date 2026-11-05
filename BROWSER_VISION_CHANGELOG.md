# Browser Vision Integration — 2026-09-29

## Added
- Browser Vision camera mode using `navigator.mediaDevices.getUserMedia()`.
- Browser frames are sent as JPEG to Flask and stored in a two-slot shared-memory buffer.
- Python MediaPipe processing can consume Browser Vision frames without opening a second OpenCV camera.
- Separate Window mode remains the existing OpenCV webcam path.
- Browser camera maximize/minimize controls.
- Camera mode is passed from dashboard to the Python engine using `AI_VM_CAMERA_MODE`.
- Dashboard status now includes `camera_mode`.

## Important
Start the Flask dashboard first. Browser Vision requires the dashboard process to own the shared-memory frame buffer.

No new third-party dependency was added.

2026-09-29 UI update:
- Reworked desktop dashboard sizing so Vision Engine stays visible in the main viewport.
- Browser Vision camera feed and maximize/minimize controls are forced visible when Browser Vision is active.
- Added dynamic Active Mode gesture instructions for Normal, Volume, Brightness, Media, and Voice modes.
- Added mode-specific gesture/action descriptions based on the current GestureEngine behavior.
- Browser Vision automatically scrolls the workspace into view after camera permission succeeds.
