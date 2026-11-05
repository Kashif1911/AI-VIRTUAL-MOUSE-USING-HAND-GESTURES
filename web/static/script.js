/* ============================================================
   AI Virtual Mouse — Dashboard
   Vanilla JS — Flask API Integration
   ============================================================ */

(function () {
  'use strict';

  const csrfToken =
    document.querySelector('meta[name="csrf-token"]')?.content || "";

  /* ── DOM refs ──────────────────────────────────────────── */
  const startBtn = document.getElementById('startBtn');
  const stopBtn  = document.getElementById('stopBtn');

  // Camera selection
const cameraChoiceModal =
    document.getElementById('cameraChoiceModal');

const browserCameraOption =
    document.getElementById('browserCameraOption');

const separateCameraOption =
    document.getElementById('separateCameraOption');

const cameraModalClose =
    document.getElementById('cameraModalClose');

const cameraModalCancel =
    document.getElementById('cameraModalCancel');

  // Camera
  const cameraFeed    = document.getElementById('cameraFeed');
  const cameraStandby = document.getElementById('cameraStandby');
  const cameraFrame   = document.querySelector('.camera-frame');
  const cameraWindowState = document.getElementById('cameraWindowState');
  const cameraViewControls = document.getElementById('cameraViewControls');
  const cameraMaximizeBtn = document.getElementById('cameraMaximizeBtn');
  const cameraMinimizeBtn = document.getElementById('cameraMinimizeBtn');

  let browserStream = null;
  let browserFrameTimer = null;
  let browserCanvas = null;
  let browserFrameBusy = false;
  let activeCameraMode = null;
  // Browser Vision is automatically handed off to the native camera while
  // this tab is hidden, because browsers throttle background-tab timers.
  let preferBrowserVision = false;
  let cameraModeSwitchBusy = false;
  let cameraModeSwitchToken = 0;

  // Telemetry values
  const mouseStatus    = document.getElementById('mouseStatus');
  const handStatus     = document.getElementById('handStatus');
  const currentGesture = document.getElementById('currentGesture');
  const fpsDisplay     = document.getElementById('fpsDisplay');
  const visionFps      = document.getElementById('visionFps');
  const perfStatus     = document.getElementById('perfStatus');
  const landmarkCount  = document.getElementById('landmarkCount');

  // Telemetry live dots
  const mouseDot   = document.getElementById('mouseDot');
  const handDot    = document.getElementById('handDot');
  const gestureDot = document.getElementById('gestureDot');
  const perfDot    = document.getElementById('perfDot');

  // Vision panel
  const liveBadge    = document.getElementById('liveBadge');
  const liveText     = document.getElementById('liveText');
  const detectionDot = document.getElementById('detectionDot');
  const detectionText= document.getElementById('detectionText');

  // Vision footer
  const overlayGesture   = document.getElementById('overlayGesture');
  const overlayMode      = document.getElementById('overlayMode');
  const overlayLandmarks = document.getElementById('overlayLandmarks');

  // Header / sidebar
  const engineStatus    = document.getElementById('engineStatus');
  const sidebarStatus   = document.getElementById('sidebarStatus');
  const sidebarStatusDot= document.getElementById('sidebarStatusDot');
  const cmdCameraStatus = document.getElementById('cmdCameraStatus');

  // Active mode
  const activeModeName = document.getElementById('activeModeName');
  const activeModeDesc = document.getElementById('activeModeDesc');

  // Mode rows + live gesture instructions
  const modeRows = document.querySelectorAll('.mode-row');
  const modeGuideTitle = document.getElementById('modeGuideTitle');
  const modeGuideCount = document.getElementById('modeGuideCount');
  const modeGuideSummary = document.getElementById('modeGuideSummary');
  const modeGuideList = document.getElementById('modeGuideList');

  const modeInstructions = {
    normal: {
      title: 'Normal Mode — Gesture Instructions',
      summary: 'Use your hand as the mouse. Perform one gesture at a time while keeping your hand inside the camera view.',
      items: [
        ['☝️', 'Move Cursor', 'Move the index-finger tip to control the Windows cursor.'],
        ['🤏', 'Left Click', 'Bring thumb + index finger together.'],
        ['🤏', 'Right Click', 'Bring thumb + middle finger together.'],
        ['🤏', 'Drag & Drop', 'Bring thumb + ring finger together and hold to drag.'],
        ['✌️', 'Scroll', 'Raise index + middle fingers and tilt the hand up/down.']
      ]
    },
    volume: {
      title: 'Volume Mode — Gesture Instructions',
      summary: 'Hold the Volume activation pose. Change volume by changing the thumb-to-index distance.',
      items: [
        ['✌️', 'Enter Volume Mode', 'Hold index + middle UP with ring + pinky DOWN.'],
        ['🤏', 'Adjust Volume', 'Move thumb and index closer/farther to decrease/increase volume.'],
        ['↩️', 'Exit', 'Release the Volume pose; the engine returns to Normal after the exit delay.']
      ]
    },
    brightness: {
      title: 'Brightness Mode — Gesture Instructions',
      summary: 'Hold the three-finger activation pose. Use thumb-to-index distance to set brightness.',
      items: [
        ['🖖', 'Enter Brightness Mode', 'Hold index + middle + ring UP with pinky DOWN.'],
        ['🤏', 'Adjust Brightness', 'Move thumb and index closer/farther to decrease/increase brightness.'],
        ['🖐️', 'Exit', 'Show an open palm to return to Normal Mode.']
      ]
    },
    media: {
      title: 'Media Mode — Gesture Instructions',
      summary: 'Activate Media Mode with the pinky-only pose, then use thumb pinches for playback controls.',
      items: [
        ['🤙', 'Enter Media Mode', 'Hold ONLY the pinky UP; index + middle + ring stay DOWN.'],
        ['🤏', 'Play / Pause', 'Thumb + index pinch.'],
        ['🤏', 'Next Track', 'Thumb + middle pinch.'],
        ['🤏', 'Previous Track', 'Thumb + ring pinch.'],
        ['🖐️', 'Exit Media Mode', 'After releasing the activation pose, show an open palm.']
      ]
    },
    voice: {
      title: 'Voice Mode — Instructions',
      summary: 'Use the offline voice assistant for supported computer commands.',
      items: [
        ['🎙️', 'Browser / Apps', 'Say “open chrome”, “open google”, “open youtube”, or “open explorer”.'],
        ['🔊', 'Audio', 'Say “mute”, “unmute”, “volume up”, or “volume down”.'],
        ['📸', 'Screenshot', 'Say “take screenshot” or “capture screen”.'],
        ['🪟', 'Window Control', 'Say “close window” to close the current window.'],
        ['⏹️', 'Voice Control', 'Say “stop” to stop voice recognition or “exit” to end the engine.']
      ]
    }
  };

  let pollTimer  = null;
  let isRunning  = false;

  /* ── Helpers ───────────────────────────────────────────── */
  function capitalize(s) {
    if (!s) return '—';
    return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
  }

  function setText(el, val) {
    if (el) el.textContent = val;
  }

  function setDotLive(el, live) {
    if (!el) return;
    live ? el.classList.add('live') : el.classList.remove('live');
  }

  /* ── Camera Choice Modal ─────────────────────────────── */

function openCameraChoiceModal() {
    if (!cameraChoiceModal) return;

    cameraChoiceModal.classList.add('is-open');
}

function closeCameraChoiceModal() {
    if (!cameraChoiceModal) return;

    cameraChoiceModal.classList.remove('is-open');
}

cameraModalClose.addEventListener(
    'click',
    closeCameraChoiceModal
);

cameraModalCancel.addEventListener(
    'click',
    closeCameraChoiceModal
);


/* Browser Vision */

browserCameraOption.addEventListener('click', function () {

    closeCameraChoiceModal();

    startVirtualMouse('browser');

});


/* Separate OpenCV Window */

separateCameraOption.addEventListener('click', function () {

    closeCameraChoiceModal();

    startVirtualMouse('window');

});


/* Start engine with selected camera mode */

function startVirtualMouse(cameraMode) {

    preferBrowserVision = cameraMode === 'browser';
    startBtn.disabled = true;

    setText(startBtn, 'Starting…');

  fetch("/api/start", {
    method: "POST",
    headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken
    },

    body: JSON.stringify({
        camera_mode: cameraMode
    })
})

    .then(function (r) {
        return r.json();
    })

    .then(function (data) {

        if (
            data.status === 'started' ||
            data.status === 'ok' ||
            data.success ||
            data.running
        ) {

            onEngineStart(cameraMode);

        } else {

            resetStartButton();

        }

    })

    .catch(function (err) {

        console.error(
            '[AI Virtual Mouse] Start failed:',
            err
        );

        resetStartButton();

    });
}

  /* ── Start handler ─────────────────────────────────────── */
  startBtn.addEventListener('click', function () {
      openCameraChoiceModal();
  });
     

  /* ── Stop handler ──────────────────────────────────────── */
  stopBtn.addEventListener('click', function () {
    preferBrowserVision = false;
    cameraModeSwitchToken++;
    stopBtn.disabled = true;
    setText(stopBtn, 'Stopping…');

    fetch('/api/stop', {
  method: 'POST',
  headers: {
    'X-CSRF-Token': csrfToken
  }
})
      .then(function (r) { return r.json(); })
      .then(function () {
        onEngineStop();
      })
      .catch(function (err) {
        console.error('[AI Virtual Mouse] Stop failed:', err);
        resetStopButton();
      });
  });

  /* ── Engine started ────────────────────────────────────── */
  function onEngineStart(cameraMode) {
    isRunning = true;
    activeCameraMode = cameraMode || 'window';

    // Button swap
    startBtn.style.display = 'none';
    resetStopButton();
    stopBtn.style.display = 'inline-flex';

    // Camera panel
    cameraStandby.style.display = 'none';
    if (cameraFrame) {
      cameraFrame.classList.remove('is-maximized');
      cameraFrame.classList.toggle(
        'browser-active',
        activeCameraMode === 'browser'
      );
      cameraFrame.classList.toggle(
        'separate-active',
        activeCameraMode === 'window'
      );
    }

    if (activeCameraMode === 'browser') {
      if (cameraWindowState) cameraWindowState.style.display = 'none';
      startBrowserVision();
    } else {
      stopBrowserVision();
      if (cameraFeed) cameraFeed.style.display = 'none';
      if (cameraViewControls) cameraViewControls.style.display = 'none';
      if (cameraWindowState) cameraWindowState.style.display = 'flex';
    }

    // Live badge
    liveBadge.classList.add('is-live');
    setText(liveText, 'Live');

    // Header
    setText(engineStatus, 'Live');
    if (engineStatus) engineStatus.style.color = 'var(--green)';

    // Camera status
    setText(
      cmdCameraStatus,
      activeCameraMode === 'browser' ? 'Browser Online' : 'Window Online'
    );
    if (cmdCameraStatus) cmdCameraStatus.style.color = 'var(--green)';

    // Telemetry dots
    setDotLive(mouseDot,   true);
    setDotLive(handDot,    true);
    setDotLive(gestureDot, true);
    setDotLive(perfDot,    true);

    setText(mouseStatus, 'Active');

    // Sidebar
    setText(sidebarStatus, 'Running');
    if (sidebarStatus) sidebarStatus.style.color = 'var(--ac)';

    document.body.classList.add('engine-running');

    startPoll();
  }

  /* ── Browser camera → Python frame pipeline ───────────── */
  async function startBrowserVision() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      console.error('[AI Virtual Mouse] Browser camera API is unavailable.');
      await stopFromBrowserFailure();
      return;
    }

    try {
      browserStream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 480 },
          height: { ideal: 360 },
          facingMode: 'user'
        },
        audio: false
      });

      cameraFeed.srcObject = browserStream;
      cameraFeed.style.display = 'block';

      await cameraFeed.play();

      if (!browserCanvas) {
        browserCanvas = document.createElement('canvas');
      }

      browserCanvas.width = 480;
      browserCanvas.height = 360;

      if (cameraViewControls) {
        cameraViewControls.style.display = 'flex';
      }

      var workspace = document.querySelector('.workspace');
      if (workspace) {
        workspace.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }

      startBrowserFrameLoop();

    } catch (err) {
      console.error(
        '[AI Virtual Mouse] Browser camera permission/start failed:',
        err
      );

      await stopFromBrowserFailure();
    }
  }

  function startBrowserFrameLoop() {
    stopBrowserFrameLoop();

    // Browser-only performance mode: 25 FPS maximum. Always skip a frame
    // if the previous upload is pending so stale frames never queue.
    browserFrameTimer = setInterval(sendBrowserFrame, 40);
  }

  function stopBrowserFrameLoop() {
    if (browserFrameTimer) {
      clearInterval(browserFrameTimer);
      browserFrameTimer = null;
    }
    browserFrameBusy = false;
  }

  async function sendBrowserFrame() {
    if (
      browserFrameBusy ||
      !browserStream ||
      !cameraFeed ||
      cameraFeed.readyState < 2 ||
      !browserCanvas
    ) {
      return;
    }

    browserFrameBusy = true;

    try {
      const ctx = browserCanvas.getContext('2d', {
        alpha: false,
        desynchronized: true
      });

      ctx.drawImage(
        cameraFeed,
        0,
        0,
        browserCanvas.width,
        browserCanvas.height
      );

      const blob = await new Promise(function (resolve) {
        browserCanvas.toBlob(resolve, 'image/jpeg', 0.55);
      });

      if (!blob || !isRunning || activeCameraMode !== 'browser') {
        return;
      }

      await fetch('/api/browser_frame', {
        method: 'POST',
        headers: {
                  "Content-Type": "image/jpeg",

          "X-CSRF-Token": csrfToken
        },
        body: blob,
        cache: 'no-store'
      });
    } catch (err) {
      console.warn(
        '[AI Virtual Mouse] Browser frame upload failed:',
        err
      );
    } finally {
      browserFrameBusy = false;
    }
  }

  function stopBrowserVision() {
    stopBrowserFrameLoop();

    if (browserStream) {
      browserStream.getTracks().forEach(function (track) {
        track.stop();
      });
      browserStream = null;
    }

    if (cameraFeed) {
      cameraFeed.pause();
      cameraFeed.srcObject = null;
      cameraFeed.style.display = 'none';
    }
  }

  /*
   * Background-tab compatibility:
   * Chrome throttles timers and video callbacks in hidden tabs. Browser Vision
   * therefore hands control to the existing native OpenCV camera when the
   * dashboard becomes hidden, and restores Browser Vision when it is visible.
   * Only one engine/camera is active at a time.
   */
  async function switchCameraModeForVisibility(targetMode) {
    if (!preferBrowserVision || !isRunning || cameraModeSwitchBusy ||
        activeCameraMode === targetMode || document.visibilityState === 'prerender') {
      return;
    }

    cameraModeSwitchBusy = true;
    const token = ++cameraModeSwitchToken;
    try {
      // Release the browser camera before starting the native camera, and
      // stop the current engine before starting the replacement.
      stopBrowserVision();
      const stopResponse = await fetch('/api/stop', {
        method: 'POST', headers: { 'X-CSRF-Token': csrfToken }
      });
      if (!stopResponse.ok) throw new Error('Could not stop the current camera engine');
      if (token !== cameraModeSwitchToken || !preferBrowserVision) return;

      const startResponse = await fetch('/api/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
        body: JSON.stringify({ camera_mode: targetMode })
      });
      const result = await startResponse.json();
      if (!startResponse.ok || !(result.success || result.running || result.status === 'started')) {
        throw new Error(result.message || 'Could not switch camera mode');
      }
      if (token !== cameraModeSwitchToken || !preferBrowserVision) {
        // A visibility change occurred mid-switch; the next visibility event
        // will bring the engine to the appropriate mode.
        return;
      }
      onEngineStart(targetMode);
      console.info('[AI Virtual Mouse] Visibility handoff:', targetMode);
    } catch (err) {
      console.warn('[AI Virtual Mouse] Camera visibility handoff failed:', err);
      // Recover to a known stopped state rather than leaving a stale Live UI.
      try { await fetch('/api/stop', { method: 'POST', headers: { 'X-CSRF-Token': csrfToken } }); } catch (_) {}
      onEngineStop();
    } finally {
      cameraModeSwitchBusy = false;
      if (preferBrowserVision && isRunning) {
        const desired = document.visibilityState === 'hidden' ? 'window' : 'browser';
        if (activeCameraMode !== desired) {
          setTimeout(function () { switchCameraModeForVisibility(desired); }, 250);
        }
      }
    }
  }

  document.addEventListener('visibilitychange', function () {
    if (!preferBrowserVision || !isRunning) return;
    switchCameraModeForVisibility(
      document.visibilityState === 'hidden' ? 'window' : 'browser'
    );
  });

  async function stopFromBrowserFailure() {
    stopBrowserVision();

    try {
      await fetch('/api/stop', { method: 'POST' });
    } catch (err) {
      console.warn(
        '[AI Virtual Mouse] Could not stop engine after browser camera failure.',
        err
      );
    }

    onEngineStop();
  }

  /* ── Camera view maximize/minimize ───────────────────── */
  if (cameraMaximizeBtn) {
    cameraMaximizeBtn.addEventListener('click', function () {
      if (!cameraFrame) return;

      cameraFrame.classList.add('is-maximized');

      if (cameraMaximizeBtn) cameraMaximizeBtn.style.display = 'none';
      if (cameraMinimizeBtn) cameraMinimizeBtn.style.display = 'inline-flex';
    });
  }

  if (cameraMinimizeBtn) {
    cameraMinimizeBtn.addEventListener('click', function () {
      if (!cameraFrame) return;

      cameraFrame.classList.remove('is-maximized');

      if (cameraMaximizeBtn) cameraMaximizeBtn.style.display = 'inline-flex';
      if (cameraMinimizeBtn) cameraMinimizeBtn.style.display = 'none';
    });
  }

  /* ── Engine stopped ────────────────────────────────────── */
  function onEngineStop() {
    preferBrowserVision = false;
    cameraModeSwitchToken++;
    isRunning = false;
    stopPoll();

    // Button swap
    stopBtn.style.display = 'none';
    resetStartButton();
    startBtn.style.display = 'inline-flex';

    // Camera
    stopBrowserVision();

    if (cameraFrame) {
      cameraFrame.classList.remove(
        'is-maximized',
        'browser-active',
        'separate-active'
      );
    }

    if (cameraViewControls) {
      cameraViewControls.style.display = 'none';
    }

    if (cameraMaximizeBtn) {
      cameraMaximizeBtn.style.display = 'inline-flex';
    }

    if (cameraMinimizeBtn) {
      cameraMinimizeBtn.style.display = 'none';
    }

    if (cameraWindowState) {
      cameraWindowState.style.display = 'none';
    }

    cameraStandby.style.display = 'flex';

    // Live badge
    liveBadge.classList.remove('is-live');
    setText(liveText, 'Standby');

    // Header
    setText(engineStatus, 'Standby');
    if (engineStatus) engineStatus.style.color = '';

    // Camera status in command
    setText(cmdCameraStatus, 'Offline');
    if (cmdCameraStatus) cmdCameraStatus.style.color = '';

    // Telemetry dots
    setDotLive(mouseDot,   false);
    setDotLive(handDot,    false);
    setDotLive(gestureDot, false);
    setDotLive(perfDot,    false);

    // Reset telemetry values
    setText(mouseStatus,    'Off');
    setText(handStatus,     'Waiting');
    setText(currentGesture, 'None');
    setText(fpsDisplay,     '— FPS');
    setText(visionFps,      '— FPS');
    setText(perfStatus,     'Standby');
    setText(landmarkCount,  '— landmarks');

    // Detection indicator
    if (detectionDot) detectionDot.classList.remove('active');
    setText(detectionText, 'No Signal');

    // Vision footer
    setText(overlayGesture,   '—');
    setText(overlayMode,      '—');
    setText(overlayLandmarks, '—');

    // Sidebar
    setText(sidebarStatus, 'AI Engine Ready');
    if (sidebarStatus) sidebarStatus.style.color = '';

    // Active mode reset
    setText(activeModeName, 'Normal Mode');
    setText(activeModeDesc, 'AI control profile active');
    setActiveMode('normal');

    // Body flag
    document.body.classList.remove('engine-running');
  }

  /* ── Poll /api/status ──────────────────────────────────── */
  function startPoll() {
    stopPoll();
    fetchStatus();
    pollTimer = setInterval(fetchStatus, 500);
  }

  function stopPoll() {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  function fetchStatus() {
    fetch('/api/status')
      .then(function (r) { return r.json(); })
      .then(function (data) { updateUI(data); })
      .catch(function (err) {
        console.warn('[AI Virtual Mouse] Status poll error:', err);
      });
  }

  /* ── Update UI from status payload ─────────────────────── */
  function updateUI(data) {
    /* ------ FPS ------ */
    var fps = data.fps || data.performance || null;
    var fpsStr = fps !== null ? (fps + ' FPS') : '— FPS';
    setText(fpsDisplay, fpsStr);
    setText(visionFps,  fpsStr);

    if (fps !== null) {
      var fpsNum = parseInt(fps, 10);
      if (!isNaN(fpsNum)) {
        if (fpsNum >= 24) {
          setText(perfStatus, 'Stable');
          if (perfStatus) perfStatus.style.color = '';
        } else if (fpsNum > 0) {
          setText(perfStatus, 'Low FPS');
          if (perfStatus) perfStatus.style.color = 'var(--amber)';
        }
      }
    }

    /* ------ Hand detection ------ */
    var handDetected = data.hand_detected || data.handDetected
                    || data.hand || false;
    var landmarks    = data.landmarks || data.hand_landmarks
                    || data.landmark_count || 21;

    setText(handStatus,    handDetected ? 'Detected'  : 'Searching');
    setText(landmarkCount, handDetected ? (landmarks + ' landmarks') : '— landmarks');
    setText(detectionText, handDetected ? 'Hand detected' : 'No signal');
    setText(overlayLandmarks, handDetected ? String(landmarks) : '—');

    if (detectionDot) {
      handDetected
        ? detectionDot.classList.add('active')
        : detectionDot.classList.remove('active');
    }

    /* ------ Gesture ------ */
    var gesture = data.gesture || data.current_gesture
               || data.currentGesture || 'None';
    var gestureLabel = capitalize(gesture);
    setText(currentGesture, gestureLabel);
    setText(overlayGesture,  gesture !== 'None' ? gestureLabel : '—');

    /* ------ Mode ------ */
    var mode = (data.mode || data.active_mode || data.activeMode
             || 'normal').toLowerCase();
    setText(overlayMode,    capitalize(mode));
    setText(activeModeName, capitalize(mode) + ' Mode');
    setText(activeModeDesc, 'AI control profile active');
    setActiveMode(mode);

    /* ------ Running flag ------ */
    var running = data.running || data.is_running || isRunning;
    setText(mouseStatus, running ? 'Active' : 'Off');
  }

  /* ── Mode row highlight ────────────────────────────────── */
  function renderModeInstructions(mode) {
    if (!modeGuideList) return;

    var key = String(mode || 'normal').toLowerCase();
    var guide = modeInstructions[key] || modeInstructions.normal;

    setText(modeGuideTitle, guide.title);
    setText(modeGuideCount, guide.items.length + (guide.items.length === 1 ? ' action' : ' actions'));
    setText(modeGuideSummary, guide.summary);

    modeGuideList.innerHTML = guide.items.map(function (item) {
      return (
        '<div class="mode-guide-item">' +
          '<div class="mode-guide-icon">' + item[0] + '</div>' +
          '<div class="mode-guide-main">' +
            '<span class="mode-guide-name">' + item[1] + '</span>' +
            '<span class="mode-guide-action">' + item[2] + '</span>' +
          '</div>' +
        '</div>'
      );
    }).join('');
  }

  function setActiveMode(mode) {
    var normalizedMode = String(mode || 'normal').toLowerCase();

    modeRows.forEach(function (row) {
      var rowMode   = row.dataset.mode;
      var statusEl  = row.querySelector('.mr-status');
      var isActive  = (rowMode === normalizedMode);
      isActive
        ? row.classList.add('active')
        : row.classList.remove('active');
      if (statusEl) {
        statusEl.textContent = isActive ? 'Active' : 'Standby';
      }
    });

    renderModeInstructions(normalizedMode);
  }

  /* ── Button reset helpers ──────────────────────────────── */
  function resetStartButton() {
    startBtn.disabled = false;
    startBtn.innerHTML =
      '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">'
      + '<polygon points="5 3 19 12 5 21 5 3"/></svg>'
      + ' Start Virtual Mouse';
  }

  function resetStopButton() {
    stopBtn.disabled = false;
    stopBtn.innerHTML =
      '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">'
      + '<rect x="6" y="6" width="12" height="12" rx="1"/></svg>'
      + ' Stop Engine';
  }

  
  /* ── Sidebar navigation ────────────────────────────────── */

  const contentRoot = document.querySelector('main.content');
  const infoPages = Array.from(
    document.querySelectorAll('.info-page[data-page]')
  );
  const navItems = Array.from(
    document.querySelectorAll('.nav-item[data-section]')
  );
  const topbarCrumb = document.querySelector('.topbar-crumb');
  const topbarTitle = document.querySelector('.topbar-title');

  const dashboardContent = contentRoot
    ? Array.from(contentRoot.children).filter(function (el) {
        return !el.matches('.info-page[data-page]');
      })
    : [];

  const sectionLabels = {
    dashboard: 'Dashboard',
    'virtual-mouse': 'Virtual Mouse',
    media: 'Media Mode',
    volume: 'Volume Mode',
    brightness: 'Brightness Mode',
    voice: 'Voice Mode',
    settings: 'Settings',
    'account-profile': 'Account Profile',
    'edit-profile': 'Edit Profile',
    'change-password': 'Change Password',
    'forgot-password': 'Reset Password',
    'delete-account': 'Delete Account'
  };

  function showSection(section, updateHash) {
    if (!sectionLabels[section]) {
      section = 'dashboard';
    }

    dashboardContent.forEach(function (el) {
      el.hidden = section !== 'dashboard';
    });

    infoPages.forEach(function (page) {
      page.hidden = page.dataset.page !== section;
    });

    navItems.forEach(function (item) {
      const active = item.dataset.section === section;
      item.classList.toggle('active', active);

      if (active) {
        item.setAttribute('aria-current', 'page');
      } else {
        item.removeAttribute('aria-current');
      }
    });

    if (topbarCrumb) {
      topbarCrumb.innerHTML =
        'Control Center <span class="crumb-arrow">›</span> ' +
        sectionLabels[section];
    }

    if (topbarTitle) {
      topbarTitle.textContent =
        section === 'dashboard' ? 'AI Virtual Mouse' : sectionLabels[section];
    }

    if (contentRoot) {
      contentRoot.scrollTop = 0;
    }

    if (updateHash && window.history && window.history.replaceState) {
      window.history.replaceState(null, '', '#' + section);
    }
  }

  /* Sidebar links */
  navItems.forEach(function (item) {
    item.addEventListener('click', function (event) {
      event.preventDefault();

      const section = item.dataset.section;

      if (section === 'account-profile') {
        loadAccountProfile();
      }

      showSection(section, true);
    });
  });

  /* Load account details */
  async function loadAccountProfile() {
    const usernameElement = document.getElementById('profileUsername');
    const emailElement = document.getElementById('profileEmail');
    const createdElement = document.getElementById('profileCreatedAt');

    if (!usernameElement || !emailElement || !createdElement) {
      return;
    }

    try {
      const response = await fetch('/account/profile', {
        method: 'GET',
        credentials: 'same-origin',
        headers: {
          Accept: 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Could not load account profile.');
      }

      const profile = await response.json();

      usernameElement.textContent = profile.username || 'Not available';
      emailElement.textContent = profile.email || 'Not available';
      createdElement.textContent = profile.created_at || 'Not available';

      const editUsernameElement =
        document.getElementById('editProfileUsername');
      const editEmailElement =
        document.getElementById('editProfileEmail');

      if (editUsernameElement) {
        editUsernameElement.value = profile.username || '';
      }

      if (editEmailElement) {
        editEmailElement.value = profile.email || '';
      }
    } catch (error) {
      usernameElement.textContent = 'Unable to load';
      emailElement.textContent = 'Unable to load';
      createdElement.textContent = 'Unable to load';

      console.error('Account profile error:', error);
    }
  }

  /* Buttons that open account/settings pages */
  document.querySelectorAll('[data-open-section]').forEach(function (button) {
    button.addEventListener('click', function () {
      const targetSection = button.dataset.openSection;

      if (targetSection === 'account-profile') {
        loadAccountProfile();
      }

      showSection(targetSection, true);
    });
  });

  /* Edit Profile form */
  const editProfileForm = document.getElementById('editProfileForm');

  if (editProfileForm) {
    editProfileForm.addEventListener('submit', async function (event) {
      event.preventDefault();

      const messageElement =
        document.getElementById('editProfileMessage');
      const submitButton =
        editProfileForm.querySelector('button[type="submit"]');

      if (!messageElement || !submitButton) {
        return;
      }

      messageElement.textContent = 'Saving changes...';
      submitButton.disabled = true;

      try {
        const formData = new FormData(editProfileForm);
        const csrfMeta = document.querySelector('meta[name="csrf-token"]');

        if (!csrfMeta) {
          throw new Error('Security token is missing. Refresh the page.');
        }

        const response = await fetch('/account/profile/update', {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'X-CSRF-Token': csrfMeta.content,
            Accept: 'application/json'
          },
          body: formData
        });

        const result = await response.json();

        if (!response.ok || !result.success) {
          throw new Error(result.message || 'Unable to update profile.');
        }

        messageElement.textContent = result.message;

        const usernameElement =
          document.getElementById('profileUsername');
        const emailElement =
          document.getElementById('profileEmail');

        if (usernameElement) {
          usernameElement.textContent = result.username;
        }

        if (emailElement) {
          emailElement.textContent = result.email;
        }

        showSection('account-profile', true);
      } catch (error) {
        messageElement.textContent =
          error.message || 'An error occurred.';
      } finally {
        submitButton.disabled = false;
      }
    });
  }

  /* Change Password form */
  const changePasswordForm =
    document.getElementById('changePasswordForm');

  if (changePasswordForm) {
    changePasswordForm.addEventListener('submit', async function (event) {
      event.preventDefault();

      const messageElement =
        document.getElementById('changePasswordMessage');
      const submitButton =
        changePasswordForm.querySelector('button[type="submit"]');
      const newPasswordElement =
        document.getElementById('newPassword');
      const confirmPasswordElement =
        document.getElementById('confirmNewPassword');

      if (
        !messageElement ||
        !submitButton ||
        !newPasswordElement ||
        !confirmPasswordElement
      ) {
        console.error('Change Password form elements are missing.');
        return;
      }

      if (newPasswordElement.value !== confirmPasswordElement.value) {
        messageElement.textContent = 'The new passwords do not match.';
        return;
      }

      const csrfMeta = document.querySelector('meta[name="csrf-token"]');

      if (!csrfMeta) {
        messageElement.textContent =
          'Security token is missing. Refresh the page and try again.';
        return;
      }

      messageElement.textContent = 'Updating password...';
      submitButton.disabled = true;

      try {
        const formData = new FormData(changePasswordForm);

        const response = await fetch('/account/password/change', {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'X-CSRF-Token': csrfMeta.content,
            Accept: 'application/json'
          },
          body: formData
        });

        const result = await response.json();

        if (!response.ok || !result.success) {
          throw new Error(result.message || 'Unable to change password.');
        }

        messageElement.textContent = result.message;
        changePasswordForm.reset();
      } catch (error) {
        messageElement.textContent =
          error.message || 'An error occurred.';
      } finally {
        submitButton.disabled = false;
      }
    });
  }

  
const forgotPasswordForm = document.getElementById("forgotPasswordForm");

if (forgotPasswordForm) {
    forgotPasswordForm.addEventListener("submit", async function (event) {
        event.preventDefault();

        const message = document.getElementById("forgotPasswordMessage");
        const submitButton = document.getElementById("forgotPasswordSubmit");
        const email = document.getElementById("forgotPasswordEmail");

        if (!message || !submitButton || !email) {
            return;
        }

        message.textContent = "Requesting password reset...";
        submitButton.disabled = true;

        try {
            const csrfMeta = document.querySelector('meta[name="csrf-token"]');
            const csrfToken = csrfMeta ? csrfMeta.content : "";

            if (!csrfToken) {
                throw new Error("Security token missing. Refresh the page and try again.");
            }

            const response = await fetch("/forgot-password", {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRF-Token": csrfToken
                },
                body: JSON.stringify({ email: email.value.trim() })
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.message || "Unable to process your request.");
            }

            message.textContent = result.message ||
                "If an account exists for that email, a reset link will be sent shortly.";
        } catch (error) {
            message.textContent = error.message || "An error occurred. Please try again.";
        } finally {
            submitButton.disabled = false;
        }
    });
}


  /* Open the requested section on page load */
  const initialSection = window.location.hash
    ? window.location.hash.slice(1)
    : 'dashboard';

  if (initialSection === 'account-profile') {
    loadAccountProfile();
  }

  showSection(initialSection, false);


  /* ── Initial check (in case Flask already running) ─────── */
  fetch('/api/status')
    .then(function (r) { return r.json(); })
    .then(function (data) {
      var running = data.running || data.is_running;
      if (running) {
        onEngineStart(data.camera_mode || 'window');
        updateUI(data);
      }
    })
    .catch(function () { /* server not ready yet, fine */ });

})();