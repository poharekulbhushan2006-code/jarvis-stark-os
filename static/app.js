/**
 * J.A.R.V.I.S. Core Operating Interface
 * Stark Industries Real-Time Holographic Client
 */

(function () {
    'use strict';

    // -------------------------------------------------------------
    // Configuration & State
    // -------------------------------------------------------------
    const CONFIG = {
        circumference: 314.159, // 2 * PI * 50
        wakeWords: [
            'jarvis', 'hey jarvis', 'you jarvis', 'yo jarvis', 'ok jarvis', 'hi jarvis',
            'wake up jarvis', 'jarvis wake up', 'turn on jarvis', 'wake up', 'friday', 'unlock'
        ],
        reconnectDelay: 2500,
    };

    const state = {
        ws: null,
        currentState: 'LISTENING', // Start in active LISTENING mode for instant response
        isSpacePressed: false,
        recognition: null,
        isContinuousListening: true,
        isAutoVoiceEnabled: true,
        isAirgapEnabled: true,
        isSfxEnabled: localStorage.getItem('jarvis_sfx') !== 'false',
        audioContext: null,
        analyser: null,
        audioSource: null,
        audioPlaying: false,
        hasGreeted: false,
        watchdogInterval: null,
        watchdogRemaining: 10,
        isShuttingDown: false,
    };

    // -------------------------------------------------------------
    // DOM Elements Cache
    // -------------------------------------------------------------
    const elements = {
        clock: document.getElementById('hudClock'),
        date: document.getElementById('hudDate'),
        connectionStatus: document.getElementById('connectionStatus'),
        aiStateBadge: document.getElementById('aiStateBadge'),
        aiStateText: document.getElementById('aiStateText'),
        coreStateLabel: document.getElementById('coreStateLabel'),
        arcCoreBtn: document.getElementById('arcCoreBtn'),
        termInfo: document.getElementById('termInfo'),

        // Futuristic Extensions (Canvas & Header Controls)
        hudParticleCanvas: document.getElementById('hudParticleCanvas'),
        btnAirGapToggle: document.getElementById('btnAirGapToggle'),
        airGapDot: document.getElementById('airGapDot'),
        airGapStatusLabel: document.getElementById('airGapStatusLabel'),
        airGapBadgeLabel: document.getElementById('airGapBadgeLabel'),
        btnSoundFX: document.getElementById('btnSoundFX'),
        sfxStatusLabel: document.getElementById('sfxStatusLabel'),
        btnCommandMatrix: document.getElementById('btnCommandMatrix'),
        btnHeaderLockdown: document.getElementById('btnHeaderLockdown'),

        // Gauges
        gaugeCpuBar: document.getElementById('gaugeCpuBar'),
        gaugeRamBar: document.getElementById('gaugeRamBar'),
        gaugeBattBar: document.getElementById('gaugeBattBar'),
        gaugeDiskBar: document.getElementById('gaugeDiskBar'),
        valCpu: document.getElementById('valCpu'),
        valRam: document.getElementById('valRam'),
        valBatt: document.getElementById('valBatt'),
        valDisk: document.getElementById('valDisk'),
        ramMeta: document.getElementById('ramMeta'),
        battMeta: document.getElementById('battMeta'),
        diskMeta: document.getElementById('diskMeta'),
        procList: document.getElementById('procList'),

        // Hardware Controls
        sliderVolume: document.getElementById('sliderVolume'),
        lblVolume: document.getElementById('lblVolume'),
        sliderBrightness: document.getElementById('sliderBrightness'),
        lblBrightness: document.getElementById('lblBrightness'),

        // Voice Toggles & Buttons
        btnWakeWord: document.getElementById('btnWakeWord'),
        wakeWordStatus: document.getElementById('wakeWordStatus'),
        btnAutoVoice: document.getElementById('btnAutoVoice'),
        autoVoiceStatus: document.getElementById('autoVoiceStatus'),
        btnMicIcon: document.getElementById('btnMicIcon'),

        // Dialogue & Input
        feedStream: document.getElementById('feedStream'),
        commandForm: document.getElementById('commandForm'),
        commandInput: document.getElementById('commandInput'),
        btnClearFeed: document.getElementById('btnClearFeed'),

        // Canvas & Audio
        canvas: document.getElementById('visualizerCanvas'),
        audioPlayer: document.getElementById('ttsAudioPlayer'),

        // Modals
        modalSettings: document.getElementById('modalSettings'),
        btnSettings: document.getElementById('btnSettings'),
        btnCloseSettings: document.getElementById('btnCloseSettings'),
        btnCancelSettings: document.getElementById('btnCancelSettings'),
        btnSaveSettings: document.getElementById('btnSaveSettings'),
        settingGeminiKey: document.getElementById('settingGeminiKey'),
        settingUserName: document.getElementById('settingUserName'),
        settingVoice: document.getElementById('settingVoice'),
        settingLockPassword: document.getElementById('settingLockPassword'),
        lockStatusTag: document.getElementById('lockStatusTag'),
        voiceStatusTag: document.getElementById('voiceStatusTag'),
        btnLaunchCalibrate: document.getElementById('btnLaunchCalibrate'),
        btnHeaderVoiceEnroll: document.getElementById('btnHeaderVoiceEnroll'),
        btnOpenVoiceEnroll: document.getElementById('btnOpenVoiceEnroll'),
        modalVoiceEnroll: document.getElementById('modalVoiceEnroll'),
        btnCloseVoiceEnroll: document.getElementById('btnCloseVoiceEnroll'),
        btnDoneVoiceEnroll: document.getElementById('btnDoneVoiceEnroll'),
        stepBadge1: document.getElementById('stepBadge1'),
        stepBadge2: document.getElementById('stepBadge2'),
        stepBadge3: document.getElementById('stepBadge3'),
        stepStatus1: document.getElementById('stepStatus1'),
        stepStatus2: document.getElementById('stepStatus2'),
        stepStatus3: document.getElementById('stepStatus3'),
        enrollPhraseText: document.getElementById('enrollPhraseText'),
        vuLevelBar: document.getElementById('vuLevelBar'),
        vuLevelValue: document.getElementById('vuLevelValue'),
        btnRecordEnrollSample: document.getElementById('btnRecordEnrollSample'),
        btnRecordEnrollText: document.getElementById('btnRecordEnrollText'),
        recordEnrollIcon: document.getElementById('recordEnrollIcon'),
        enrollTimer: document.getElementById('enrollTimer'),
        enrollSecondsRemaining: document.getElementById('enrollSecondsRemaining'),
        enrollFeedback: document.getElementById('enrollFeedback'),
        voiceTestSection: document.getElementById('voiceTestSection'),
        btnTestVoiceMatch: document.getElementById('btnTestVoiceMatch'),
        testMatchResult: document.getElementById('testMatchResult'),
        btnResetEnrollment: document.getElementById('btnResetEnrollment'),
        btnLaunchCalibrateBat: document.getElementById('btnLaunchCalibrateBat'),
        settingsAlert: document.getElementById('settingsAlert'),

        modalScreenshots: document.getElementById('modalScreenshots'),
        btnScreenshots: document.getElementById('btnScreenshots'),
        btnCloseScreenshots: document.getElementById('btnCloseScreenshots'),
        screenshotsGrid: document.getElementById('screenshotsGrid'),

        modalNotes: document.getElementById('modalNotes'),
        btnNotes: document.getElementById('btnNotes'),
        btnCloseNotes: document.getElementById('btnCloseNotes'),
        notesList: document.getElementById('notesList'),

        // Tactical Command Matrix Modal
        modalCommandMatrix: document.getElementById('modalCommandMatrix'),
        btnCloseCommandMatrix: document.getElementById('btnCloseCommandMatrix'),
        matrixSearchInput: document.getElementById('matrixSearchInput'),
        matrixItemsGrid: document.getElementById('matrixItemsGrid'),

        // OmniRoute Gateway
        omniroutePill: document.getElementById('omniroutePill'),
        omniDot: document.getElementById('omniDot'),
        omniModelBadge: document.getElementById('omniModelBadge'),
        btnOmniRoute: document.getElementById('btnOmniRoute'),
        modalOmniRoute: document.getElementById('modalOmniRoute'),
        btnCloseOmniRoute: document.getElementById('btnCloseOmniRoute'),
        btnDoneOmniRoute: document.getElementById('btnDoneOmniRoute'),
        gwStatStatus: document.getElementById('gwStatStatus'),
        gwStatModel: document.getElementById('gwStatModel'),

        // System Media Deck
        btnMediaPrev: document.getElementById('btnMediaPrev'),
        btnMediaPlayPause: document.getElementById('btnMediaPlayPause'),
        btnMediaNext: document.getElementById('btnMediaNext'),
        btnMediaStop: document.getElementById('btnMediaStop'),
        mediaTrackLabel: document.getElementById('mediaTrackLabel'),
        mediaWaveAnim: document.getElementById('mediaWaveAnim'),

        // Workspace Automation Deck
        btnShowDesktop: document.getElementById('btnShowDesktop'),
        btnSwitchWindow: document.getElementById('btnSwitchWindow'),
        btnReadClipboard: document.getElementById('btnReadClipboard'),
        btnAnalyzeScreen: document.getElementById('btnAnalyzeScreen'),

        // Left Panel Security Deck
        btnToggleAirGapAction: document.getElementById('btnToggleAirGapAction'),
        btnToggleAirGapLabel: document.getElementById('btnToggleAirGapLabel'),
        secShieldTitle: document.getElementById('secShieldTitle'),
        secBadgeStatus: document.getElementById('secBadgeStatus'),
        secLeaksBlocked: document.getElementById('secLeaksBlocked'),
        secLocalPort: document.getElementById('secLocalPort'),
        secDpapiVal: document.getElementById('secDpapiVal'),
        secBioVal: document.getElementById('secBioVal'),
        btnEngageLockdown: document.getElementById('btnEngageLockdown'),

        // Standby & 10-Second Watchdog Controls
        btnHeaderStandby: document.getElementById('btnHeaderStandby'),
        watchdogBanner: document.getElementById('watchdogBanner'),
        watchdogSeconds: document.getElementById('watchdogSeconds'),
        watchdogProgressBar: document.getElementById('watchdogProgressBar'),
        btnDisarmWatchdog: document.getElementById('btnDisarmWatchdog'),
        shutdownOverlay: document.getElementById('shutdownOverlay'),
        shutdownStatusMsg: document.getElementById('shutdownStatusMsg'),
    };

    // -------------------------------------------------------------
    // 1. Clock & Date Initialization
    // -------------------------------------------------------------
    function updateClock() {
        const now = new Date();
        const timeOptions = { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true };
        const dateOptions = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        
        elements.clock.textContent = now.toLocaleTimeString([], timeOptions).toUpperCase();
        elements.date.textContent = now.toLocaleDateString([], dateOptions).toUpperCase();
    }
    setInterval(updateClock, 1000);
    updateClock();

    // -------------------------------------------------------------
    // 2. HUD State Management
    // -------------------------------------------------------------
    function setAiState(newState) {
        state.currentState = newState;
        document.body.classList.remove('state-standby', 'state-listening', 'state-processing', 'state-speaking');
        document.body.classList.add(`state-${newState.toLowerCase()}`);

        elements.aiStateText.textContent = newState;
        elements.coreStateLabel.textContent = newState === 'STANDBY' ? 'VOICE READY' : newState;

        if (newState === 'LISTENING') {
            elements.termInfo.textContent = 'MICROPHONE OPEN // DETECTING VOCAL SPECTRUM...';
        } else if (newState === 'PROCESSING') {
            elements.termInfo.textContent = 'NEURAL ENGINE PROCESSING QUERY...';
        } else if (newState === 'SPEAKING') {
            elements.termInfo.textContent = 'AUDIO TRANSMISSION ACTIVE // SYNTHESIS ONLINE';
        } else {
            elements.termInfo.textContent = 'READY FOR INPUT // STANDBY';
        }
    }

    // -------------------------------------------------------------
    // 3. Telemetry Gauges Renderer
    // -------------------------------------------------------------
    function updateRadialGauge(barEl, valEl, percent) {
        const p = Math.max(0, Math.min(100, percent));
        const offset = CONFIG.circumference - (p / 100) * CONFIG.circumference;
        barEl.style.strokeDashoffset = offset;
        valEl.textContent = `${Math.round(p)}%`;
    }

    function renderTelemetry(data) {
        if (!data) return;

        // CPU
        if (data.cpu_percent !== undefined) {
            updateRadialGauge(elements.gaugeCpuBar, elements.valCpu, data.cpu_percent);
        }

        // RAM
        if (data.ram_percent !== undefined) {
            updateRadialGauge(elements.gaugeRamBar, elements.valRam, data.ram_percent);
            elements.ramMeta.textContent = `${data.ram_used_gb} GB / ${data.ram_total_gb} GB`;
        }

        // Battery
        if (data.battery) {
            const batt = data.battery;
            updateRadialGauge(elements.gaugeBattBar, elements.valBatt, batt.percent);
            elements.battMeta.textContent = batt.status_text;
            if (batt.is_low) {
                elements.gaugeBattBar.style.stroke = 'var(--crimson-alert)';
            } else {
                elements.gaugeBattBar.style.stroke = 'var(--emerald-active)';
            }
        }

        // Disk
        if (data.disk_percent !== undefined) {
            updateRadialGauge(elements.gaugeDiskBar, elements.valDisk, data.disk_percent);
            elements.diskMeta.textContent = `${data.disk_free_gb} GB Free`;
        }

        // Volume & Brightness Sliders (only if user is not currently dragging)
        if (data.volume !== undefined && !elements.sliderVolume.matches(':active')) {
            elements.sliderVolume.value = data.volume;
            elements.lblVolume.textContent = `${data.volume}%`;
        }

        if (data.brightness !== undefined && !elements.sliderBrightness.matches(':active')) {
            elements.sliderBrightness.value = data.brightness;
            elements.lblBrightness.textContent = `${data.brightness}%`;
        }

        // Process List
        if (data.top_processes && Array.isArray(data.top_processes)) {
            elements.procList.innerHTML = '';
            data.top_processes.forEach(p => {
                const item = document.createElement('div');
                item.className = 'proc-item';
                item.innerHTML = `
                    <span class="proc-name" title="${p.name}">${p.name}</span>
                    <span class="proc-stats">${p.mem_percent}% RAM</span>
                `;
                elements.procList.appendChild(item);
            });
        }
    }

    // -------------------------------------------------------------
    // 4. WebSocket Real-Time Channel
    // -------------------------------------------------------------
    function initWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        state.ws = new WebSocket(wsUrl);

        state.ws.onopen = () => {
            elements.connectionStatus.textContent = 'ONLINE';
            elements.connectionStatus.style.color = 'var(--emerald-active)';
            elements.termInfo.textContent = 'SYSTEMS LINKED // WEBSOCKET SECURED';

            // Play startup welcome audio greeting
            if (!state.hasGreeted) {
                state.hasGreeted = true;
                fetch('/api/welcome')
                    .then(res => res.json())
                    .then(data => {
                        if (data && data.audio_url && state.isAutoVoiceEnabled) {
                            playAudio(data.audio_url);
                        }
                    })
                    .catch(() => {});
            }
        };

        state.ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                if (msg.type === 'INIT') {
                    renderTelemetry(msg.telemetry);
                    if (msg.security) {
                        const isAirgap = msg.security.airgap_active !== undefined ? msg.security.airgap_active : (msg.security.airgap_mode ?? true);
                        const leaks = msg.security.outbound_leaks_prevented !== undefined ? msg.security.outbound_leaks_prevented : (msg.security.leaks_prevented || 0);
                        updateAirGapUI(isAirgap);
                        if (elements.secLeaksBlocked) elements.secLeaksBlocked.textContent = leaks;
                        if (elements.airGapBadgeLabel) elements.airGapBadgeLabel.textContent = `${leaks}B LEAK`;
                        if (elements.secDpapiVal) elements.secDpapiVal.textContent = msg.security.dpapi_hardware_encrypted ? 'ENCRYPTED' : 'READY';
                        if (elements.secBioVal) elements.secBioVal.textContent = 'LOCAL MFCC';
                    }
                } else if (msg.type === 'SECURITY_UPDATE') {
                    const isAirgap = msg.airgap_active !== undefined ? msg.airgap_active : (msg.airgap_mode !== undefined ? msg.airgap_mode : (msg.data?.airgap_active ?? true));
                    const leaks = msg.leaks_prevented !== undefined ? msg.leaks_prevented : (msg.data?.outbound_leaks_prevented ?? 0);
                    updateAirGapUI(isAirgap);
                    if (elements.secLeaksBlocked) elements.secLeaksBlocked.textContent = leaks;
                    if (elements.airGapBadgeLabel) elements.airGapBadgeLabel.textContent = `${leaks}B LEAK`;
                } else if (msg.type === 'LOCKDOWN') {
                    playHudSound('lockdown');
                    appendFeedMessage('JARVIS', msg.message || 'EMERGENCY PROTOCOL: Workstation locked.', 'SECURITY_LOCKDOWN');
                } else if (msg.type === 'TELEMETRY_UPDATE') {
                    renderTelemetry(msg.data);
                } else if (msg.type === 'STATE_CHANGE') {
                    setAiState(msg.state);
                } else if (msg.type === 'COMMAND_RESULT') {
                    handleCommandResult(msg.result);
                } else if (msg.type === 'WAKE_TRIGGER') {
                    startWatchdogTimer(msg.countdown_seconds || 10);
                    if (msg.result) {
                        handleCommandResult(msg.result);
                    }
                    setAiState('LISTENING');
                    if (!isRecognitionActive) {
                        try { state.recognition && state.recognition.start(); } catch (err) {}
                    }
                } else if (msg.type === 'WATCHDOG_DISARM') {
                    disarmWatchdogTimer(false);
                } else if (msg.type === 'AUTO_SHUTDOWN') {
                    triggerShutdownSequence(msg.message || "Powering down systems and returning to silent standby...", msg.audio_url);
                }
            } catch (err) {
                console.error('[JARVIS WS Error]', err);
            }
        };

        state.ws.onclose = () => {
            elements.connectionStatus.textContent = 'RECONNECTING';
            elements.connectionStatus.style.color = 'var(--amber-warn)';
            setTimeout(initWebSocket, CONFIG.reconnectDelay);
        };

        state.ws.onerror = () => {
            elements.connectionStatus.textContent = 'OFFLINE';
            elements.connectionStatus.style.color = 'var(--crimson-alert)';
        };
    }

    // -------------------------------------------------------------
    // 5. Command Transmission & Dialogue Feed
    // -------------------------------------------------------------
    function sendCommand(text) {
        const clean = text.trim();
        if (!clean) return;

        // Disarm 10-second inactivity watchdog on user instruction
        disarmWatchdogTimer(true);

        // Add user bubble to feed
        appendFeedMessage('USER', clean);
        setAiState('PROCESSING');

        // Transmit via WebSocket if open, else fallback to REST
        if (state.ws && state.ws.readyState === WebSocket.OPEN) {
            state.ws.send(JSON.stringify({ type: 'COMMAND', query: clean }));
        } else {
            fetch('/api/command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: clean })
            })
            .then(res => res.json())
            .then(handleCommandResult)
            .catch(err => {
                appendFeedMessage('JARVIS', `Communication failure: ${err.message}`, 'ERROR');
                setAiState('STANDBY');
            });
        }
    }

    function appendFeedMessage(sender, text, actionTag) {
        const isUser = sender === 'USER';
        const item = document.createElement('div');
        item.className = `feed-item ${isUser ? 'user-item' : 'jarvis-item'}`;

        const now = new Date();
        const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        let tagHtml = '';
        if (actionTag) {
            tagHtml = `<div class="feed-action-tag">[${actionTag}]</div>`;
        }

        item.innerHTML = `
            <div class="feed-avatar">${isUser ? 'U' : 'J'}</div>
            <div class="feed-content">
                <div class="feed-meta">
                    <span class="author">${isUser ? 'USER' : 'J.A.R.V.I.S.'}</span>
                    <span class="feed-time">${timeStr}</span>
                </div>
                <div class="feed-text">${escapeHtml(text)}</div>
                ${tagHtml}
            </div>
        `;

        elements.feedStream.appendChild(item);
        elements.feedStream.scrollTop = elements.feedStream.scrollHeight;
    }

    function escapeHtml(str) {
        return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function handleCommandResult(res) {
        if (!res) {
            setAiState('STANDBY');
            return;
        }

        // Disarm watchdog on any completed interaction
        disarmWatchdogTimer(false);

        // Add Jarvis response to dialogue feed
        appendFeedMessage('JARVIS', res.text, res.action);

        // Play voice audio if enabled
        if (state.isAutoVoiceEnabled && res.audio_url) {
            playAudio(res.audio_url);
        } else {
            setAiState('STANDBY');
        }

        // If action is SYSTEM_STANDBY, initiate holographic shutdown sequence
        if (res.action === 'SYSTEM_STANDBY') {
            triggerShutdownSequence(res.text || "Entering silent standby mode...", res.audio_url);
        }
    }

    // -------------------------------------------------------------
    // 5.5 Watchdog Auto-Shutdown & Holographic Standby System
    // -------------------------------------------------------------
    function startWatchdogTimer(seconds = 10) {
        if (state.isShuttingDown) return;
        clearInterval(state.watchdogInterval);
        state.watchdogRemaining = seconds;

        if (elements.watchdogBanner) {
            elements.watchdogBanner.style.display = 'block';
            if (elements.watchdogSeconds) elements.watchdogSeconds.textContent = seconds;
            if (elements.watchdogProgressBar) {
                elements.watchdogProgressBar.style.transition = 'none';
                elements.watchdogProgressBar.style.width = '100%';
                setTimeout(() => {
                    if (elements.watchdogProgressBar) {
                        elements.watchdogProgressBar.style.transition = `width ${seconds}s linear`;
                        elements.watchdogProgressBar.style.width = '0%';
                    }
                }, 50);
            }
        }

        state.watchdogInterval = setInterval(() => {
            state.watchdogRemaining -= 1;
            if (elements.watchdogSeconds) {
                elements.watchdogSeconds.textContent = Math.max(0, state.watchdogRemaining);
            }
            if (state.watchdogRemaining <= 0) {
                clearInterval(state.watchdogInterval);
            }
        }, 1000);
    }

    function disarmWatchdogTimer(notifyBackend = false) {
        if (state.watchdogInterval) {
            clearInterval(state.watchdogInterval);
            state.watchdogInterval = null;
        }
        if (elements.watchdogBanner) {
            elements.watchdogBanner.style.display = 'none';
        }
        if (notifyBackend) {
            fetch('/api/system/disarm-watchdog', { method: 'POST' }).catch(() => {});
            if (state.ws && state.ws.readyState === WebSocket.OPEN) {
                state.ws.send(JSON.stringify({ type: 'WATCHDOG_DISARM' }));
            }
        }
    }

    function triggerShutdownSequence(message = "Returning systems to silent standby mode...", audioUrl = null) {
        if (state.isShuttingDown) return;
        state.isShuttingDown = true;
        disarmWatchdogTimer(false);

        if (elements.shutdownOverlay) {
            elements.shutdownOverlay.style.display = 'flex';
        }
        if (elements.shutdownStatusMsg) {
            elements.shutdownStatusMsg.textContent = message;
        }

        if (audioUrl) {
            playAudio(audioUrl);
        }

        if (state.ws) {
            state.ws.onclose = null; // Do not attempt reconnect
            try { state.ws.close(); } catch (e) {}
        }

        setTimeout(() => {
            try {
                window.open('', '_self', '');
                window.close();
            } catch (e) {}
            setTimeout(() => {
                if (elements.shutdownStatusMsg) {
                    elements.shutdownStatusMsg.textContent = "SYSTEM STANDBY ACTIVE // Tab can be safely closed or minimized.";
                }
            }, 600);
        }, 2500);
    }

    // -------------------------------------------------------------
    // 6. Web Audio API, Sound Synthesizer & Spectrum Visualizer
    // -------------------------------------------------------------
    function initAudioContext() {
        if (!state.audioContext) {
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            state.audioContext = new AudioCtx();
            state.analyser = state.audioContext.createAnalyser();
            state.analyser.fftSize = 64;

            state.audioSource = state.audioContext.createMediaElementSource(elements.audioPlayer);
            state.audioSource.connect(state.analyser);
            state.analyser.connect(state.audioContext.destination);

            drawVisualizer();
        }
        if (state.audioContext.state === 'suspended') {
            state.audioContext.resume();
        }
    }

    function playHudSound(type) {
        if (!state.isSfxEnabled && type !== 'lockdown') return;
        try {
            initAudioContext();
            const ctx = state.audioContext;
            if (!ctx) return;
            const now = ctx.currentTime;
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);

            if (type === 'click') {
                // Crisp holographic button click
                osc.type = 'sine';
                osc.frequency.setValueAtTime(1800, now);
                osc.frequency.exponentialRampToValueAtTime(450, now + 0.04);
                gain.gain.setValueAtTime(0.06, now);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.05);
                osc.start(now);
                osc.stop(now + 0.05);
            } else if (type === 'alert') {
                // Security Alert Double Pulse
                osc.type = 'sawtooth';
                osc.frequency.setValueAtTime(880, now);
                osc.frequency.setValueAtTime(440, now + 0.1);
                gain.gain.setValueAtTime(0.08, now);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.22);
                osc.start(now);
                osc.stop(now + 0.22);
            } else if (type === 'lockdown') {
                // Heavy workstation lockdown tone
                osc.type = 'sawtooth';
                osc.frequency.setValueAtTime(320, now);
                osc.frequency.exponentialRampToValueAtTime(55, now + 0.5);
                gain.gain.setValueAtTime(0.22, now);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.6);
                osc.start(now);
                osc.stop(now + 0.6);
            } else if (type === 'chirp' || type === 'listen') {
                // High-tech Stark activation blip
                osc.type = 'sine';
                osc.frequency.setValueAtTime(600, now);
                osc.frequency.exponentialRampToValueAtTime(1200, now + 0.08);
                gain.gain.setValueAtTime(0.08, now);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.12);
                osc.start(now);
                osc.stop(now + 0.12);
            } else if (type === 'transmit') {
                // Confirmation chirp
                osc.type = 'triangle';
                osc.frequency.setValueAtTime(880, now);
                osc.frequency.exponentialRampToValueAtTime(1760, now + 0.1);
                gain.gain.setValueAtTime(0.06, now);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.14);
                osc.start(now);
                osc.stop(now + 0.14);
            } else if (type === 'power') {
                // Arc reactor power-up hum
                osc.type = 'sine';
                osc.frequency.setValueAtTime(130, now);
                osc.frequency.exponentialRampToValueAtTime(520, now + 0.22);
                gain.gain.setValueAtTime(0.12, now);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.3);
                osc.start(now);
                osc.stop(now + 0.3);
            }
        } catch (e) {}
    }

    function playAudio(audioUrl) {
        initAudioContext();
        elements.audioPlayer.src = audioUrl;
        setAiState('SPEAKING');

        elements.audioPlayer.play().catch(err => {
            console.warn('[Audio Play Autoplay Blocked]', err);
            setAiState('LISTENING');
            safeRestartRecognition(300);
        });

        elements.audioPlayer.onended = () => {
            setAiState('LISTENING');
            safeRestartRecognition(300);
        };

        elements.audioPlayer.onerror = () => {
            setAiState('LISTENING');
            safeRestartRecognition(300);
        };
    }

    function drawVisualizer() {
        requestAnimationFrame(drawVisualizer);
        const canvas = elements.canvas;
        const ctx = canvas.getContext('2d');
        const bufferLength = state.analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);

        state.analyser.getByteFrequencyData(dataArray);

        ctx.clearRect(0, 0, canvas.width, canvas.height);

        const barWidth = (canvas.width / bufferLength) * 1.5;
        let x = 0;

        for (let i = 0; i < bufferLength; i++) {
            let barHeight = (dataArray[i] / 255) * canvas.height * 0.9;
            
            // Baseline idle flutter
            if (state.currentState === 'STANDBY' && barHeight < 6) {
                barHeight = Math.sin(Date.now() / 300 + i) * 3 + 4;
            } else if (state.currentState === 'LISTENING' && barHeight < 12) {
                barHeight = Math.sin(Date.now() / 150 + i) * 6 + 10;
            }

            // High-tech holographic gradient
            const grad = ctx.createLinearGradient(0, canvas.height, 0, 0);
            if (state.currentState === 'LISTENING') {
                grad.addColorStop(0, 'rgba(0, 255, 170, 0.2)');
                grad.addColorStop(1, 'rgba(0, 255, 170, 0.95)');
            } else if (state.currentState === 'PROCESSING') {
                grad.addColorStop(0, 'rgba(255, 170, 0, 0.2)');
                grad.addColorStop(1, 'rgba(255, 170, 0, 0.95)');
            } else {
                grad.addColorStop(0, 'rgba(0, 102, 255, 0.2)');
                grad.addColorStop(1, 'rgba(0, 240, 255, 0.95)');
            }

            ctx.fillStyle = grad;
            ctx.shadowBlur = 8;
            ctx.shadowColor = state.currentState === 'LISTENING' ? '#00ffaa' : '#00f0ff';

            ctx.fillRect(x, canvas.height - barHeight, barWidth - 4, barHeight);
            x += barWidth;
        }
    }

    // -------------------------------------------------------------
    // 7. Speech Recognition (Speech-to-Text & Wake Word)
    // -------------------------------------------------------------
    let isRecognitionActive = false;
    let recognitionWatchdog = null;

    function safeRestartRecognition(delay = 400) {
        clearTimeout(recognitionWatchdog);
        if (!state.isContinuousListening || state.currentState === 'SPEAKING') return;

        recognitionWatchdog = setTimeout(() => {
            if (!state.recognition || isRecognitionActive) return;
            try {
                state.recognition.start();
            } catch (e) {
                // Ignore InvalidStateError if already running
            }
        }, delay);
    }

    function initSpeechRecognition() {
        const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRec) {
            console.warn('[Speech Recognition] Web Speech API not supported in this browser.');
            elements.termInfo.textContent = 'WEB SPEECH API UNAVAILABLE // USE TEXT OR PUSH-TO-TALK';
            return;
        }

        state.recognition = new SpeechRec();
        state.recognition.continuous = true;
        state.recognition.interimResults = false;
        state.recognition.lang = 'en-US';

        state.recognition.onstart = () => {
            isRecognitionActive = true;
            elements.termInfo.textContent = 'NEURAL AUDIO LINK ACTIVE // LISTENING CONTINUOUSLY...';
        };

        state.recognition.onresult = (event) => {
            const last = event.results.length - 1;
            const transcript = event.results[last][0].transcript.trim();
            if (!transcript) return;

            console.log('[Transcript Heard]:', transcript);

            // Any speech received disarms 10-second inactivity watchdog immediately
            disarmWatchdogTimer(true);

            // Wake word matching
            let isWakeWordTriggered = false;
            let query = transcript;
            const lower = transcript.toLowerCase();

            for (const w of CONFIG.wakeWords) {
                if (lower.startsWith(w)) {
                    isWakeWordTriggered = true;
                    query = transcript.slice(w.length).replace(/^[,:\s]+/, '').trim();
                    break;
                } else if (lower.includes(w)) {
                    isWakeWordTriggered = true;
                    query = transcript.replace(new RegExp(w, 'gi'), '').replace(/^[,:\s]+/, '').trim();
                    break;
                }
            }

            // In active HUD mode, execute command directly!
            if (state.currentState === 'LISTENING' || state.isSpacePressed || state.isAutoVoiceEnabled || isWakeWordTriggered) {
                playHudSound('transmit');
                const commandToSend = query || transcript;
                if (commandToSend.length > 0) {
                    sendCommand(commandToSend);
                } else {
                    sendCommand("hello");
                }
                return;
            }

            // In continuous standby listening mode, trigger on wake word
            if (isWakeWordTriggered) {
                playHudSound('transmit');
                if (query.length > 0) {
                    sendCommand(query);
                } else {
                    sendCommand("hello");
                }
            }
        };

        state.recognition.onerror = (event) => {
            isRecognitionActive = false;
            if (event.error === 'not-allowed') {
                elements.termInfo.textContent = 'MICROPHONE BLOCKED // PLEASE ALLOW MIC IN BROWSER';
            } else if (event.error === 'network') {
                console.warn('[Speech Recognition Network Notice] Cloud speech offline, auto-reconnecting...');
                safeRestartRecognition(1000);
            } else if (event.error !== 'no-speech') {
                console.warn('[Speech Error]', event.error);
                safeRestartRecognition(600);
            }
        };

        state.recognition.onend = () => {
            isRecognitionActive = false;
            // Auto restart if continuous listening is on and not currently speaking audio
            if (state.isContinuousListening && state.currentState !== 'SPEAKING') {
                safeRestartRecognition(300);
            }
        };

        if (state.isContinuousListening) {
            try { state.recognition.start(); } catch (e) {}
        }
    }

    // -------------------------------------------------------------
    // 8. Event Listeners & Hardware Controls
    // -------------------------------------------------------------
    // Spacebar Push-to-Talk (with repeat check to avoid duplicate key crash)
    window.addEventListener('keydown', (e) => {
        disarmWatchdogTimer(true);
        if (e.repeat) return; // Prevent repeated rapid-fire events while key is held down
        if (e.code === 'Space' && document.activeElement !== elements.commandInput) {
            e.preventDefault();
            state.isSpacePressed = true;
            initAudioContext();
            playHudSound('chirp');
            setAiState('LISTENING');
            if (!isRecognitionActive) {
                try { state.recognition && state.recognition.start(); } catch (err) {}
            }
        }
    });

    window.addEventListener('keyup', (e) => {
        if (e.code === 'Space' && state.isSpacePressed) {
            e.preventDefault();
            state.isSpacePressed = false;
            if (state.currentState === 'LISTENING') {
                setTimeout(() => {
                    if (state.currentState === 'LISTENING') {
                        setAiState('STANDBY');
                    }
                }, 300);
            }
        }
    });

    // Arc Core Click to Speak Toggle
    elements.arcCoreBtn.addEventListener('click', () => {
        initAudioContext();
        if (state.currentState === 'LISTENING') {
            setAiState('STANDBY');
            playHudSound('transmit');
        } else {
            setAiState('LISTENING');
            playHudSound('power');
            if (!isRecognitionActive) {
                try { state.recognition && state.recognition.start(); } catch (e) {}
            }
        }
    });

    // Mic Icon Button
    elements.btnMicIcon.addEventListener('click', () => {
        initAudioContext();
        elements.arcCoreBtn.click();
    });

    // Command Form Submit
    elements.commandForm.addEventListener('submit', (e) => {
        e.preventDefault();
        initAudioContext();
        const val = elements.commandInput.value;
        elements.commandInput.value = '';
        sendCommand(val);
    });

    // Quick Command Chips
    document.querySelectorAll('.chip-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            initAudioContext();
            const cmd = btn.getAttribute('data-cmd');
            sendCommand(cmd);
        });
    });

    // Volume Slider
    let volTimeout;
    elements.sliderVolume.addEventListener('input', (e) => {
        const val = e.target.value;
        elements.lblVolume.textContent = `${val}%`;
        clearTimeout(volTimeout);
        volTimeout = setTimeout(() => {
            sendCommand(`set volume to ${val}`);
        }, 400);
    });

    // Brightness Slider
    let brightTimeout;
    elements.sliderBrightness.addEventListener('input', (e) => {
        const val = e.target.value;
        elements.lblBrightness.textContent = `${val}%`;
        clearTimeout(brightTimeout);
        brightTimeout = setTimeout(() => {
            sendCommand(`set brightness to ${val}`);
        }, 400);
    });

    // Wake Word Toggle Button
    elements.btnWakeWord.addEventListener('click', () => {
        state.isContinuousListening = !state.isContinuousListening;
        elements.btnWakeWord.classList.toggle('active', state.isContinuousListening);
        elements.wakeWordStatus.textContent = state.isContinuousListening ? 'ACTIVE' : 'MUTED';
        if (state.isContinuousListening) {
            try { state.recognition && state.recognition.start(); } catch (e) {}
        } else {
            try { state.recognition && state.recognition.stop(); } catch (e) {}
        }
    });

    // Auto Voice Audio Toggle
    elements.btnAutoVoice.addEventListener('click', () => {
        state.isAutoVoiceEnabled = !state.isAutoVoiceEnabled;
        elements.btnAutoVoice.classList.toggle('active', state.isAutoVoiceEnabled);
        elements.autoVoiceStatus.textContent = state.isAutoVoiceEnabled ? 'ON' : 'MUTED';
        if (!state.isAutoVoiceEnabled) {
            elements.audioPlayer.pause();
            if (state.currentState === 'SPEAKING') setAiState('STANDBY');
        }
    });

    // Clear Dialogue Feed
    elements.btnClearFeed.addEventListener('click', () => {
        elements.feedStream.innerHTML = '';
        appendFeedMessage('JARVIS', 'Command stream purged, Sir. Systems standing by.', 'PURGED');
    });

    // -------------------------------------------------------------
    // 9. Modals (Settings, Screenshots, Notes)
    // -------------------------------------------------------------
    // Open Settings
    elements.btnSettings.addEventListener('click', () => {
        fetch('/api/settings')
            .then(r => r.json())
            .then(data => {
                elements.settingUserName.value = data.user_name || 'Sir';
                elements.settingVoice.value = data.voice || 'en-GB-RyanNeural';
                elements.settingGeminiKey.value = '';
                elements.settingGeminiKey.placeholder = data.gemini_configured 
                    ? `Key active (${data.gemini_api_key_masked})` 
                    : 'Paste API Key here (or leave blank)';

                if (elements.lockStatusTag) {
                    elements.lockStatusTag.textContent = data.password_configured ? 'CONFIGURED (DPAPI)' : 'NOT CONFIGURED';
                    elements.lockStatusTag.style.color = data.password_configured ? 'var(--emerald-active)' : 'rgba(255,255,255,0.4)';
                    elements.lockStatusTag.style.background = data.password_configured ? 'rgba(0,255,170,0.15)' : 'rgba(255,255,255,0.08)';
                }
                if (elements.voiceStatusTag) {
                    elements.voiceStatusTag.textContent = data.voice_enrolled ? 'ENROLLED (AUTHENTICATED)' : 'NOT ENROLLED';
                    elements.voiceStatusTag.style.color = data.voice_enrolled ? 'var(--emerald-active)' : 'rgba(255,255,255,0.4)';
                    elements.voiceStatusTag.style.background = data.voice_enrolled ? 'rgba(0,255,170,0.15)' : 'rgba(255,255,255,0.08)';
                }
                if (elements.settingLockPassword) elements.settingLockPassword.value = '';

                elements.settingsAlert.style.display = 'none';
                elements.modalSettings.classList.add('active');
            });
    });

    elements.btnCloseSettings.addEventListener('click', () => elements.modalSettings.classList.remove('active'));
    elements.btnCancelSettings.addEventListener('click', () => elements.modalSettings.classList.remove('active'));

    // ========================================================
    // BIOMETRIC VOICE ENROLLMENT & CALIBRATION SYSTEM
    // ========================================================
    const ENROLL_PHRASES = [
        "Jarvis, all systems are online.",
        "Jarvis, unlock workstation.",
        "Jarvis, run diagnostics."
    ];
    let enrollCurrentStep = 1;
    let isEnrolling = false;

    // Helper: Encodes Float32 audio buffer into 16-bit PCM RIFF WAV Blob
    function encodeFloat32ToWav(samples, sampleRate) {
        const buffer = new ArrayBuffer(44 + samples.length * 2);
        const view = new DataView(buffer);

        function writeString(offset, str) {
            for (let i = 0; i < str.length; i++) {
                view.setUint8(offset + i, str.charCodeAt(i));
            }
        }

        writeString(0, 'RIFF');
        view.setUint32(4, 36 + samples.length * 2, true);
        writeString(8, 'WAVE');
        writeString(12, 'fmt ');
        view.setUint32(16, 16, true);
        view.setUint16(20, 1, true); // PCM
        view.setUint16(22, 1, true); // Mono
        view.setUint32(24, sampleRate, true);
        view.setUint32(28, sampleRate * 2, true); // Byte rate (16-bit)
        view.setUint16(32, 2, true); // Block align
        view.setUint16(34, 16, true); // Bits per sample
        writeString(36, 'data');
        view.setUint32(40, samples.length * 2, true);

        let offset = 44;
        for (let i = 0; i < samples.length; i++, offset += 2) {
            const s = Math.max(-1, Math.min(1, samples[i]));
            view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
        }
        return new Blob([buffer], { type: 'audio/wav' });
    }

    function updateEnrollBadges() {
        const badges = [elements.stepBadge1, elements.stepBadge2, elements.stepBadge3];
        const statuses = [elements.stepStatus1, elements.stepStatus2, elements.stepStatus3];

        badges.forEach((b, idx) => {
            const stepNum = idx + 1;
            if (!b) return;
            const titleSpan = b.querySelector('span:first-child');
            if (stepNum < enrollCurrentStep) {
                b.style.borderColor = 'var(--emerald-active)';
                b.style.background = 'rgba(0, 255, 170, 0.12)';
                if (titleSpan) titleSpan.style.color = 'var(--emerald-active)';
                if (statuses[idx]) {
                    statuses[idx].textContent = 'ACCEPTED ✓';
                    statuses[idx].style.color = 'var(--emerald-active)';
                }
            } else if (stepNum === enrollCurrentStep) {
                b.style.borderColor = 'var(--accent-cyan)';
                b.style.background = 'rgba(0, 217, 255, 0.12)';
                if (titleSpan) titleSpan.style.color = 'var(--accent-cyan)';
                if (statuses[idx]) {
                    statuses[idx].textContent = 'CURRENT';
                    statuses[idx].style.color = 'var(--accent-cyan)';
                }
            } else {
                b.style.borderColor = 'rgba(255, 255, 255, 0.15)';
                b.style.background = 'rgba(0, 0, 0, 0.3)';
                if (titleSpan) titleSpan.style.color = '#888';
                if (statuses[idx]) {
                    statuses[idx].textContent = 'PENDING';
                    statuses[idx].style.color = '#888';
                }
            }
        });

        if (elements.enrollPhraseText && enrollCurrentStep <= 3) {
            elements.enrollPhraseText.textContent = `"${ENROLL_PHRASES[enrollCurrentStep - 1]}"`;
        }
    }

    function openVoiceEnrollModal() {
        if (!elements.modalVoiceEnroll) return;
        elements.modalVoiceEnroll.classList.add('active');

        // Check current status
        fetch('/api/biometrics/status')
            .then(r => r.json())
            .then(data => {
                if (data.enrolled) {
                    if (elements.voiceTestSection) elements.voiceTestSection.style.display = 'block';
                    if (elements.enrollFeedback) {
                        elements.enrollFeedback.style.display = 'block';
                        elements.enrollFeedback.style.background = 'rgba(0, 255, 170, 0.12)';
                        elements.enrollFeedback.style.color = 'var(--emerald-active)';
                        elements.enrollFeedback.textContent = `Voiceprint currently active for ${data.user_name || 'Sir'}. You may re-calibrate or test recognition below.`;
                    }
                } else {
                    if (elements.voiceTestSection) elements.voiceTestSection.style.display = 'none';
                    if (elements.enrollFeedback) elements.enrollFeedback.style.display = 'none';
                }
                updateEnrollBadges();
            })
            .catch(() => updateEnrollBadges());
    }

    if (elements.btnOpenVoiceEnroll) {
        elements.btnOpenVoiceEnroll.addEventListener('click', () => {
            if (elements.modalSettings) elements.modalSettings.classList.remove('active');
            openVoiceEnrollModal();
        });
    }

    if (elements.btnHeaderVoiceEnroll) {
        elements.btnHeaderVoiceEnroll.addEventListener('click', () => {
            if (elements.modalSettings) elements.modalSettings.classList.remove('active');
            openVoiceEnrollModal();
        });
    }

    if (elements.btnCloseVoiceEnroll) {
        elements.btnCloseVoiceEnroll.addEventListener('click', () => {
            elements.modalVoiceEnroll.classList.remove('active');
        });
    }

    if (elements.btnDoneVoiceEnroll) {
        elements.btnDoneVoiceEnroll.addEventListener('click', () => {
            elements.modalVoiceEnroll.classList.remove('active');
        });
    }

    // Launch Desktop BAT tool
    const triggerDesktopBat = () => {
        fetch('/api/biometrics/launch-calibration', { method: 'POST' })
            .then(r => r.json())
            .then(res => {
                const target = elements.enrollFeedback || elements.settingsAlert;
                if (target) {
                    target.textContent = 'Voice registration terminal launched on your desktop! Please follow the prompts.';
                    target.style.display = 'block';
                    target.style.background = 'rgba(0, 217, 255, 0.15)';
                    target.style.color = 'var(--accent-cyan)';
                }
            })
            .catch(() => {
                const target = elements.enrollFeedback || elements.settingsAlert;
                if (target) {
                    target.textContent = 'Could not launch terminal automatically. Double-click register_voice.bat.';
                    target.style.display = 'block';
                }
            });
    };

    if (elements.btnLaunchCalibrate) {
        elements.btnLaunchCalibrate.addEventListener('click', triggerDesktopBat);
    }
    if (elements.btnLaunchCalibrateBat) {
        elements.btnLaunchCalibrateBat.addEventListener('click', triggerDesktopBat);
    }

    // In-Browser Audio Recording with Real-time VU meter
    async function recordAudioSnippet(durationSec, onProgress) {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const source = audioCtx.createMediaStreamSource(stream);
        const analyser = audioCtx.createAnalyser();
        analyser.fftSize = 256;
        source.connect(analyser);

        const scriptNode = audioCtx.createScriptProcessor(4096, 1, 1);
        const chunks = [];
        scriptNode.onaudioprocess = (e) => {
            const input = e.inputBuffer.getChannelData(0);
            chunks.push(new Float32Array(input));
        };

        const silentGain = audioCtx.createGain();
        silentGain.gain.value = 0;
        source.connect(scriptNode);
        scriptNode.connect(silentGain);
        silentGain.connect(audioCtx.destination);

        const dataArray = new Uint8Array(analyser.frequencyBinCount);
        let animId = null;

        function checkVu() {
            analyser.getByteFrequencyData(dataArray);
            let sum = 0;
            for (let i = 0; i < dataArray.length; i++) sum += dataArray[i];
            const avg = sum / dataArray.length;
            const pct = Math.min(100, Math.round((avg / 128) * 100));

            if (elements.vuLevelBar) elements.vuLevelBar.style.width = pct + '%';
            if (elements.vuLevelValue) elements.vuLevelValue.textContent = pct + '%';

            animId = requestAnimationFrame(checkVu);
        }
        checkVu();

        // Timer countdown
        const startTime = Date.now();
        const interval = setInterval(() => {
            const elapsed = (Date.now() - startTime) / 1000;
            const remaining = Math.max(0, durationSec - elapsed);
            if (onProgress) onProgress(remaining);
        }, 100);

        await new Promise(resolve => setTimeout(resolve, durationSec * 1000));

        clearInterval(interval);
        cancelAnimationFrame(animId);
        if (elements.vuLevelBar) elements.vuLevelBar.style.width = '0%';
        if (elements.vuLevelValue) elements.vuLevelValue.textContent = '0%';

        // Teardown
        scriptNode.disconnect();
        silentGain.disconnect();
        source.disconnect();
        stream.getTracks().forEach(t => t.stop());

        // Flatten chunks
        let totalLen = chunks.reduce((acc, c) => acc + c.length, 0);
        let combined = new Float32Array(totalLen);
        let offset = 0;
        for (let c of chunks) {
            combined.set(c, offset);
            offset += c.length;
        }

        const sampleRate = audioCtx.sampleRate;
        audioCtx.close();

        return { samples: combined, sampleRate };
    }

    // Record Enroll Sample Action
    if (elements.btnRecordEnrollSample) {
        elements.btnRecordEnrollSample.addEventListener('click', async () => {
            if (isEnrolling) return;
            isEnrolling = true;

            hudAudio.chirp(880, 'sine', 0.1);
            elements.btnRecordEnrollText.textContent = 'LISTENING... SPEAK NOW!';
            elements.recordEnrollIcon.style.background = '#00ffaa';
            elements.recordEnrollIcon.style.boxShadow = '0 0 12px #00ffaa';
            elements.enrollTimer.style.display = 'block';
            elements.enrollFeedback.style.display = 'none';

            try {
                const { samples, sampleRate } = await recordAudioSnippet(4.2, (rem) => {
                    elements.enrollSecondsRemaining.textContent = rem.toFixed(1) + 's';
                });

                // Check peak volume
                let peak = 0;
                for (let i = 0; i < samples.length; i++) {
                    const v = Math.abs(samples[i]);
                    if (v > peak) peak = v;
                }

                if (peak < 0.012) {
                    hudAudio.chirp(300, 'sawtooth', 0.2);
                    elements.enrollFeedback.textContent = `Acoustic energy was faint (Peak: ${peak.toFixed(3)} < 0.012). Please speak closer to your microphone or louder.`;
                    elements.enrollFeedback.style.display = 'block';
                    elements.enrollFeedback.style.background = 'rgba(255, 170, 0, 0.15)';
                    elements.enrollFeedback.style.color = '#ffaa00';
                    elements.btnRecordEnrollText.textContent = 'RETRY THIS PHRASE';
                    elements.recordEnrollIcon.style.background = '#ffaa00';
                    elements.recordEnrollIcon.style.boxShadow = '0 0 8px #ffaa00';
                    elements.enrollTimer.style.display = 'none';
                    isEnrolling = false;
                    return;
                }

                // Encode WAV
                const wavBlob = encodeFloat32ToWav(samples, sampleRate);
                elements.btnRecordEnrollText.textContent = 'PROCESSING ACOUSTIC SIGNATURE...';

                // Send sample to server
                const resp = await fetch(`/api/biometrics/enroll-sample?sample_index=${enrollCurrentStep}`, {
                    method: 'POST',
                    body: wavBlob,
                    headers: { 'Content-Type': 'audio/wav' }
                });
                const result = await resp.json();

                if (!result.success) {
                    elements.enrollFeedback.textContent = result.error || 'Sample validation failed. Please retry.';
                    elements.enrollFeedback.style.display = 'block';
                    elements.enrollFeedback.style.background = 'rgba(255, 51, 68, 0.15)';
                    elements.enrollFeedback.style.color = '#ff3344';
                    elements.btnRecordEnrollText.textContent = 'RETRY PHRASE';
                    isEnrolling = false;
                    return;
                }

                // Sample success
                hudAudio.chirp(1046.5, 'triangle', 0.15);
                elements.enrollFeedback.textContent = `Phrase ${enrollCurrentStep} accepted! (Peak energy: ${result.peak})`;
                elements.enrollFeedback.style.display = 'block';
                elements.enrollFeedback.style.background = 'rgba(0, 255, 170, 0.12)';
                elements.enrollFeedback.style.color = 'var(--emerald-active)';

                if (enrollCurrentStep < 3) {
                    enrollCurrentStep++;
                    updateEnrollBadges();
                    elements.btnRecordEnrollText.textContent = `RECORD PHRASE ${enrollCurrentStep} (4 SEC)`;
                    elements.recordEnrollIcon.style.background = '#ff3344';
                    elements.recordEnrollIcon.style.boxShadow = '0 0 8px #ff3344';
                } else {
                    // Finalize 3 samples
                    elements.btnRecordEnrollText.textContent = 'TRAINING ACOUSTIC CENTROID...';
                    const finResp = await fetch('/api/biometrics/finalize', { method: 'POST' });
                    const finResult = await finResp.json();

                    if (finResult.success) {
                        hudAudio.pulse();
                        elements.enrollFeedback.textContent = `✅ VOICEPRINT CALIBRATED AND ACTIVATED FOR ${finResult.user_name || 'SIR'}!`;
                        elements.btnRecordEnrollText.textContent = 'ENROLLMENT COMPLETE ✓';
                        elements.recordEnrollIcon.style.background = '#00ffaa';
                        elements.recordEnrollIcon.style.boxShadow = '0 0 15px #00ffaa';
                        if (elements.voiceTestSection) elements.voiceTestSection.style.display = 'block';

                        // Play Jarvis audio confirmation
                        if (finResult.audio_url && elements.audioPlayer) {
                            elements.audioPlayer.src = finResult.audio_url;
                            elements.audioPlayer.play().catch(() => {});
                        }

                        // Update tag in settings
                        if (elements.voiceStatusTag) {
                            elements.voiceStatusTag.textContent = 'ENROLLED (AUTHENTICATED)';
                            elements.voiceStatusTag.style.color = 'var(--emerald-active)';
                            elements.voiceStatusTag.style.background = 'rgba(0,255,170,0.15)';
                        }
                    } else {
                        elements.enrollFeedback.textContent = finResult.error || 'Failed to finalize voiceprint.';
                        elements.enrollFeedback.style.color = '#ff3344';
                    }
                }
            } catch (err) {
                console.error(err);
                elements.enrollFeedback.textContent = 'Microphone access error: ' + err.message;
                elements.enrollFeedback.style.display = 'block';
                elements.enrollFeedback.style.color = '#ff3344';
                elements.btnRecordEnrollText.textContent = 'RETRY';
            } finally {
                elements.enrollTimer.style.display = 'none';
                isEnrolling = false;
            }
        });
    }

    // Live Voice Verification Test
    if (elements.btnTestVoiceMatch) {
        elements.btnTestVoiceMatch.addEventListener('click', async () => {
            elements.testMatchResult.innerHTML = '<span style="color: var(--accent-cyan);">Listening (3.5 sec)... Speak any command or sentence now!</span>';
            hudAudio.chirp(880, 'sine', 0.1);

            try {
                const { samples, sampleRate } = await recordAudioSnippet(3.5);
                const wavBlob = encodeFloat32ToWav(samples, sampleRate);
                elements.testMatchResult.innerHTML = '<span style="color: #ffaa00;">Extracting MFCC features and verifying against Boss voiceprint...</span>';

                const resp = await fetch('/api/biometrics/test', {
                    method: 'POST',
                    body: wavBlob,
                    headers: { 'Content-Type': 'audio/wav' }
                });
                const res = await resp.json();

                if (res.is_authenticated) {
                    hudAudio.chirp(1046.5, 'triangle', 0.18);
                    elements.testMatchResult.innerHTML = `<span style="color: var(--emerald-active); font-weight: bold;">✅ AUTHENTICATED: ${res.similarity}% Match (>= ${res.threshold}% threshold) — Sir Recognized!</span>`;
                } else {
                    hudAudio.chirp(300, 'sawtooth', 0.2);
                    elements.testMatchResult.innerHTML = `<span style="color: #ffaa00;">⚠️ MATCH SCORE: ${res.similarity}% (< ${res.threshold}% threshold). Voice signature active.</span>`;
                }
            } catch (e) {
                elements.testMatchResult.innerHTML = `<span style="color: #ff3344;">Test error: ${e.message}</span>`;
            }
        });
    }

    // Reset Voiceprint
    if (elements.btnResetEnrollment) {
        elements.btnResetEnrollment.addEventListener('click', async () => {
            if (!confirm("Are you sure you want to clear your enrolled voiceprint and reset biometric authentication?")) return;

            await fetch('/api/biometrics/reset', { method: 'POST' });
            enrollCurrentStep = 1;
            updateEnrollBadges();
            if (elements.voiceTestSection) elements.voiceTestSection.style.display = 'none';
            if (elements.enrollFeedback) {
                elements.enrollFeedback.textContent = 'Voiceprint reset. You may now record fresh calibration samples.';
                elements.enrollFeedback.style.display = 'block';
                elements.enrollFeedback.style.background = 'rgba(0, 217, 255, 0.12)';
                elements.enrollFeedback.style.color = 'var(--accent-cyan)';
            }
            if (elements.btnRecordEnrollText) elements.btnRecordEnrollText.textContent = 'RECORD PHRASE 1 (4 SEC)';
            if (elements.voiceStatusTag) {
                elements.voiceStatusTag.textContent = 'NOT ENROLLED';
                elements.voiceStatusTag.style.color = 'rgba(255,255,255,0.4)';
                elements.voiceStatusTag.style.background = 'rgba(255,255,255,0.08)';
            }
            hudAudio.chirp(440, 'triangle', 0.1);
        });
    }

    // Save Settings
    elements.btnSaveSettings.addEventListener('click', () => {
        const payload = {
            user_name: elements.settingUserName.value.trim(),
            voice: elements.settingVoice.value
        };
        const key = elements.settingGeminiKey.value.trim();
        if (key) payload.gemini_api_key = key;

        if (elements.settingLockPassword && elements.settingLockPassword.value.trim()) {
            payload.lockscreen_password = elements.settingLockPassword.value.trim();
        }

        fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(r => r.json())
        .then(res => {
            elements.settingsAlert.textContent = res.message || 'Settings saved successfully.';
            elements.settingsAlert.style.display = 'block';
            elements.settingsAlert.style.background = 'rgba(0, 255, 170, 0.15)';
            elements.settingsAlert.style.color = 'var(--emerald-active)';
            setTimeout(() => {
                elements.modalSettings.classList.remove('active');
            }, 1200);
        });
    });

    // Open Screenshots Gallery
    elements.btnScreenshots.addEventListener('click', () => {
        fetch('/api/screenshots')
            .then(r => r.json())
            .then(data => {
                elements.screenshotsGrid.innerHTML = '';
                if (!data.screenshots || data.screenshots.length === 0) {
                    elements.screenshotsGrid.innerHTML = '<div class="gallery-empty">No screenshots captured yet. Click 📸 SCREENSHOT below!</div>';
                } else {
                    data.screenshots.forEach(sc => {
                        const card = document.createElement('div');
                        card.className = 'screenshot-card';
                        card.innerHTML = `
                            <a href="${sc.url}" target="_blank">
                                <img src="${sc.url}" alt="${sc.filename}" loading="lazy">
                            </a>
                            <div class="screenshot-card-name">${sc.filename}</div>
                        `;
                        elements.screenshotsGrid.appendChild(card);
                    });
                }
                elements.modalScreenshots.classList.add('active');
            });
    });
    elements.btnCloseScreenshots.addEventListener('click', () => elements.modalScreenshots.classList.remove('active'));

    // Open Notes
    elements.btnNotes.addEventListener('click', () => {
        fetch('/api/notes')
            .then(r => r.json())
            .then(data => {
                elements.notesList.innerHTML = '';
                if (!data.notes || data.notes.length === 0) {
                    elements.notesList.innerHTML = '<div class="gallery-empty">No notes recorded yet. Say "take a note: [message]" to save one.</div>';
                } else {
                    data.notes.forEach(n => {
                        const item = document.createElement('div');
                        item.className = 'note-item';
                        item.innerHTML = `
                            <div class="note-title">${escapeHtml(n.filename)}</div>
                            <div class="note-body">${escapeHtml(n.preview)}</div>
                        `;
                        elements.notesList.appendChild(item);
                    });
                }
                elements.modalNotes.classList.add('active');
            });
    });
    elements.btnCloseNotes.addEventListener('click', () => elements.modalNotes.classList.remove('active'));

    // Close modals on outside click
    window.addEventListener('click', (e) => {
        if (e.target.classList.contains('hud-modal')) {
            e.target.classList.remove('active');
        }
    });

    // -------------------------------------------------------------
    // 10. Media & Workspace Automation Handlers
    // -------------------------------------------------------------
    async function sendMediaControl(action) {
        try {
            const res = await fetch('/api/media/control', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action })
            });
            const data = await res.json();
            const actUpper = action.toUpperCase();
            appendFeedMessage('JARVIS', `Media control triggered: ${actUpper}. ${data.message || ''}`, 'MEDIA');
            if (elements.mediaTrackLabel) {
                elements.mediaTrackLabel.textContent = `STATUS: ${actUpper} TRIGGERED`;
            }
        } catch (err) {
            console.error('Media control failed:', err);
            appendFeedMessage('JARVIS', `Media command error: ${err.message}`, 'ERROR');
        }
    }

    if (elements.btnMediaPrev) elements.btnMediaPrev.addEventListener('click', () => sendMediaControl('prev'));
    if (elements.btnMediaPlayPause) elements.btnMediaPlayPause.addEventListener('click', () => sendMediaControl('play_pause'));
    if (elements.btnMediaNext) elements.btnMediaNext.addEventListener('click', () => sendMediaControl('next'));
    if (elements.btnMediaStop) elements.btnMediaStop.addEventListener('click', () => sendMediaControl('stop'));

    async function sendWindowControl(action) {
        try {
            const res = await fetch('/api/window/control', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action })
            });
            const data = await res.json();
            appendFeedMessage('JARVIS', `Workspace action executed: ${action.replace('_', ' ').toUpperCase()}`, 'WORKSPACE');
        } catch (err) {
            console.error('Window control failed:', err);
        }
    }

    if (elements.btnShowDesktop) elements.btnShowDesktop.addEventListener('click', () => sendWindowControl('minimize_all'));
    if (elements.btnSwitchWindow) elements.btnSwitchWindow.addEventListener('click', () => sendWindowControl('switch'));
    if (elements.btnReadClipboard) elements.btnReadClipboard.addEventListener('click', () => sendCommand('read my clipboard'));
    if (elements.btnAnalyzeScreen) elements.btnAnalyzeScreen.addEventListener('click', () => sendCommand('analyze screen'));

    // -------------------------------------------------------------
    // 11. OmniRoute AI Gateway Status & Modal
    // -------------------------------------------------------------
    async function pollOmniRouteStatus() {
        try {
            const res = await fetch('/api/omniroute/status');
            const data = await res.json();
            if (data.online) {
                if (elements.omniDot) elements.omniDot.style.background = 'var(--emerald-active)';
                if (elements.omniModelBadge) elements.omniModelBadge.textContent = 'ONLINE / 20128';
                if (elements.gwStatStatus) {
                    elements.gwStatStatus.textContent = 'ONLINE';
                    elements.gwStatStatus.style.color = 'var(--emerald-active)';
                }
                if (elements.gwStatModel) elements.gwStatModel.textContent = 'AUTO-COMBO';
            } else {
                if (elements.omniDot) elements.omniDot.style.background = 'var(--crimson-alert)';
                if (elements.omniModelBadge) elements.omniModelBadge.textContent = 'STANDBY';
                if (elements.gwStatStatus) {
                    elements.gwStatStatus.textContent = 'STANDBY';
                    elements.gwStatStatus.style.color = 'var(--crimson-alert)';
                }
            }
        } catch (e) {
            // Unreachable
        }
    }

    setInterval(pollOmniRouteStatus, 6000);
    pollOmniRouteStatus();

    if (elements.btnOmniRoute) {
        elements.btnOmniRoute.addEventListener('click', () => {
            pollOmniRouteStatus();
            elements.modalOmniRoute.classList.add('active');
        });
    }

    if (elements.omniroutePill) {
        elements.omniroutePill.addEventListener('click', () => {
            pollOmniRouteStatus();
            elements.modalOmniRoute.classList.add('active');
        });
    }

    if (elements.btnCloseOmniRoute) {
        elements.btnCloseOmniRoute.addEventListener('click', () => {
            elements.modalOmniRoute.classList.remove('active');
        });
    }

    if (elements.btnDoneOmniRoute) {
        elements.btnDoneOmniRoute.addEventListener('click', () => {
            elements.modalOmniRoute.classList.remove('active');
        });
    }

    // Standby & Watchdog Buttons
    if (elements.btnDisarmWatchdog) {
        elements.btnDisarmWatchdog.addEventListener('click', (e) => {
            e.stopPropagation();
            disarmWatchdogTimer(true);
        });
    }

    if (elements.btnHeaderStandby) {
        elements.btnHeaderStandby.addEventListener('click', () => {
            fetch('/api/system/shutdown', { method: 'POST' }).catch(() => {});
            triggerShutdownSequence('Powering down systems and returning to silent standby...');
        });
    }

    // Any click or interaction inside HUD disarms the watchdog
    document.addEventListener('click', () => {
        disarmWatchdogTimer(true);
    });

    // -------------------------------------------------------------
    // 12. Futuristic Particle Canvas Background
    // -------------------------------------------------------------
    function initBackgroundParticles() {
        const canvas = elements.hudParticleCanvas;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        let width = canvas.width = window.innerWidth;
        let height = canvas.height = window.innerHeight;

        window.addEventListener('resize', () => {
            width = canvas.width = window.innerWidth;
            height = canvas.height = window.innerHeight;
        });

        const particles = [];
        const count = Math.min(55, Math.floor((width * height) / 26000));
        for (let i = 0; i < count; i++) {
            particles.push({
                x: Math.random() * width,
                y: Math.random() * height,
                vx: (Math.random() - 0.5) * 0.45,
                vy: (Math.random() - 0.5) * 0.45,
                r: Math.random() * 1.5 + 0.8,
                alpha: Math.random() * 0.5 + 0.25,
                isCyan: Math.random() > 0.35
            });
        }

        let mouseX = -1000;
        let mouseY = -1000;
        window.addEventListener('mousemove', (e) => {
            mouseX = e.clientX;
            mouseY = e.clientY;
        });

        function renderFrame() {
            ctx.clearRect(0, 0, width, height);

            for (let i = 0; i < particles.length; i++) {
                const p = particles[i];
                p.x += p.vx;
                p.y += p.vy;

                if (p.x < 0) p.x = width;
                else if (p.x > width) p.x = 0;
                if (p.y < 0) p.y = height;
                else if (p.y > height) p.y = 0;

                // Render particle
                ctx.beginPath();
                ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
                ctx.fillStyle = p.isCyan
                    ? `rgba(0, 240, 255, ${p.alpha})`
                    : `rgba(0, 255, 170, ${p.alpha})`;
                ctx.fill();

                // Connect nearby particles
                for (let j = i + 1; j < particles.length; j++) {
                    const p2 = particles[j];
                    const dx = p.x - p2.x;
                    const dy = p.y - p2.y;
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    if (dist < 110) {
                        ctx.beginPath();
                        ctx.moveTo(p.x, p.y);
                        ctx.lineTo(p2.x, p2.y);
                        const strokeAlpha = (1 - dist / 110) * 0.15;
                        ctx.strokeStyle = `rgba(0, 240, 255, ${strokeAlpha})`;
                        ctx.lineWidth = 0.7;
                        ctx.stroke();
                    }
                }

                // Mouse interaction
                const mdx = p.x - mouseX;
                const mdy = p.y - mouseY;
                const mdist = Math.sqrt(mdx * mdx + mdy * mdy);
                if (mdist < 130) {
                    ctx.beginPath();
                    ctx.moveTo(p.x, p.y);
                    ctx.lineTo(mouseX, mouseY);
                    const mouseAlpha = (1 - mdist / 130) * 0.22;
                    ctx.strokeStyle = `rgba(0, 255, 170, ${mouseAlpha})`;
                    ctx.lineWidth = 0.8;
                    ctx.stroke();
                }
            }
            requestAnimationFrame(renderFrame);
        }
        renderFrame();
    }

    // -------------------------------------------------------------
    // 13. Air-Gap Privacy Shield & Security Management
    // -------------------------------------------------------------
    function updateAirGapUI(isAirgapActive) {
        state.isAirgapEnabled = !!isAirgapActive;
        if (elements.btnAirGapToggle) {
            elements.btnAirGapToggle.classList.toggle('active', state.isAirgapEnabled);
            elements.btnAirGapToggle.classList.toggle('disarmed', !state.isAirgapEnabled);
        }
        if (elements.airGapStatusLabel) {
            elements.airGapStatusLabel.textContent = state.isAirgapEnabled ? 'SECURED // LOCAL' : 'DISARMED // HYBRID';
        }
        if (elements.secShieldTitle) {
            elements.secShieldTitle.textContent = state.isAirgapEnabled ? 'AIR-GAP ISOLATION ACTIVE' : 'AIR-GAP DE-ELEVATED';
        }
        if (elements.secBadgeStatus) {
            elements.secBadgeStatus.textContent = state.isAirgapEnabled ? 'ARMED' : 'DISARMED';
            elements.secBadgeStatus.classList.toggle('active', state.isAirgapEnabled);
            elements.secBadgeStatus.classList.toggle('disarmed', !state.isAirgapEnabled);
        }
        if (elements.btnToggleAirGapAction) {
            elements.btnToggleAirGapAction.classList.toggle('active', state.isAirgapEnabled);
            elements.btnToggleAirGapAction.classList.toggle('disarmed', !state.isAirgapEnabled);
        }
        if (elements.btnToggleAirGapLabel) {
            elements.btnToggleAirGapLabel.textContent = state.isAirgapEnabled 
                ? 'AIR-GAP SHIELD: ENGAGED' 
                : 'AIR-GAP SHIELD: DISARMED';
        }
    }

    async function fetchSecurityStatus() {
        try {
            const res = await fetch('/api/security/status');
            const data = await res.json();
            const leaks = data.outbound_leaks_prevented !== undefined ? data.outbound_leaks_prevented : (data.leaks_prevented || 0);
            const isAirgap = data.airgap_active !== undefined ? data.airgap_active : (data.airgap_mode !== undefined ? data.airgap_mode : true);
            if (elements.secLeaksBlocked) elements.secLeaksBlocked.textContent = leaks;
            if (elements.airGapBadgeLabel) elements.airGapBadgeLabel.textContent = `${leaks}B LEAK`;
            if (elements.secLocalPort) elements.secLocalPort.textContent = '8000';
            if (elements.secDpapiVal) elements.secDpapiVal.textContent = data.dpapi_hardware_encrypted ? 'ENCRYPTED' : 'READY';
            if (elements.secBioVal) elements.secBioVal.textContent = 'LOCAL MFCC';
            updateAirGapUI(isAirgap);
        } catch (err) {
            console.warn('Security status fetch failed:', err);
        }
    }

    async function toggleAirGapShield() {
        playHudSound('chirp');
        const nextState = !state.isAirgapEnabled;
        try {
            const res = await fetch('/api/security/toggle-airgap', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled: nextState })
            });
            const data = await res.json();
            const isAirgap = data.airgap_active !== undefined ? data.airgap_active : (data.airgap_mode !== undefined ? data.airgap_mode : nextState);
            updateAirGapUI(isAirgap);
            const actionText = isAirgap ? "Air-Gap Isolation engaged. 100% on-device processing with zero data leakage." : "Air-Gap Shield disarmed. Cloud AI fallback permitted.";
            appendFeedMessage('JARVIS', data.message || actionText, 'SECURITY');
        } catch (err) {
            appendFeedMessage('JARVIS', `Failed to toggle air-gap: ${err.message}`, 'ERROR');
        }
    }

    async function triggerEmergencyLockdown() {
        playHudSound('lockdown');
        appendFeedMessage('JARVIS', 'EMERGENCY PROTOCOL ENGAGED: Locking Windows workstation and securing systems...', 'SECURITY_LOCKDOWN');
        try {
            await fetch('/api/security/lockdown', { method: 'POST' });
        } catch (err) {
            console.error('Lockdown request error:', err);
        }
    }

    if (elements.btnAirGapToggle) {
        elements.btnAirGapToggle.addEventListener('click', toggleAirGapShield);
    }
    if (elements.btnToggleAirGapAction) {
        elements.btnToggleAirGapAction.addEventListener('click', toggleAirGapShield);
    }
    if (elements.btnHeaderLockdown) {
        elements.btnHeaderLockdown.addEventListener('click', triggerEmergencyLockdown);
    }
    if (elements.btnEngageLockdown) {
        elements.btnEngageLockdown.addEventListener('click', triggerEmergencyLockdown);
    }

    // -------------------------------------------------------------
    // 14. Futuristic Sound FX (SFX) Synthesizer Toggle
    // -------------------------------------------------------------
    function initSoundFXToggle() {
        if (!elements.btnSoundFX) return;
        elements.btnSoundFX.classList.toggle('active', state.isSfxEnabled);
        elements.btnSoundFX.classList.toggle('muted', !state.isSfxEnabled);
        if (elements.sfxStatusLabel) elements.sfxStatusLabel.textContent = state.isSfxEnabled ? 'ON' : 'OFF';

        elements.btnSoundFX.addEventListener('click', () => {
            state.isSfxEnabled = !state.isSfxEnabled;
            localStorage.setItem('jarvis_sfx', state.isSfxEnabled);
            elements.btnSoundFX.classList.toggle('active', state.isSfxEnabled);
            elements.btnSoundFX.classList.toggle('muted', !state.isSfxEnabled);
            if (elements.sfxStatusLabel) elements.sfxStatusLabel.textContent = state.isSfxEnabled ? 'ON' : 'OFF';
            if (state.isSfxEnabled) playHudSound('chirp');
        });
    }

    // -------------------------------------------------------------
    // 15. Tactical Command Matrix Modal
    // -------------------------------------------------------------
    function initCommandMatrix() {
        if (elements.btnCommandMatrix) {
            elements.btnCommandMatrix.addEventListener('click', () => {
                playHudSound('click');
                elements.modalCommandMatrix.classList.add('active');
            });
        }
        if (elements.btnCloseCommandMatrix) {
            elements.btnCloseCommandMatrix.addEventListener('click', () => {
                elements.modalCommandMatrix.classList.remove('active');
            });
        }

        // Live Search Filter
        if (elements.matrixSearchInput) {
            elements.matrixSearchInput.addEventListener('input', (e) => {
                const query = e.target.value.toLowerCase().trim();
                const items = document.querySelectorAll('.matrix-item');
                items.forEach(item => {
                    const cmd = item.getAttribute('data-cmd') || '';
                    const desc = item.querySelector('.matrix-desc')?.textContent || '';
                    const cat = item.getAttribute('data-cat') || '';
                    const matches = cmd.toLowerCase().includes(query) || 
                                    desc.toLowerCase().includes(query) || 
                                    cat.toLowerCase().includes(query);
                    item.style.display = matches ? 'flex' : 'none';
                });
            });
        }

        // Category Filter Buttons
        const filterButtons = document.querySelectorAll('.matrix-filter-btn');
        filterButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                playHudSound('click');
                filterButtons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                const cat = btn.getAttribute('data-cat');
                const items = document.querySelectorAll('.matrix-item');
                items.forEach(item => {
                    if (cat === 'all' || item.getAttribute('data-cat') === cat) {
                        item.style.display = 'flex';
                    } else {
                        item.style.display = 'none';
                    }
                });
                if (elements.matrixSearchInput) elements.matrixSearchInput.value = '';
            });
        });

        // Click-to-Run Directive Cards
        document.querySelectorAll('.matrix-item').forEach(item => {
            item.addEventListener('click', () => {
                playHudSound('click');
                const cmd = item.getAttribute('data-cmd');
                if (cmd) {
                    elements.modalCommandMatrix.classList.remove('active');
                    sendCommand(cmd);
                }
            });
        });
    }

    // -------------------------------------------------------------
    // Boot Initialization
    // -------------------------------------------------------------
    initWebSocket();
    initSpeechRecognition();
    initBackgroundParticles();
    initSoundFXToggle();
    initCommandMatrix();
    fetchSecurityStatus();

})();
