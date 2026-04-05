/* MindstormLLM Profile Builder - Frontend */

// --- Sliders ---
document.getElementById('maxSpeed').oninput = function() {
    document.getElementById('maxSpeedVal').textContent = this.value;
};
document.getElementById('defaultSpeed').oninput = function() {
    document.getElementById('defaultSpeedVal').textContent = this.value;
};
document.getElementById('llmTemp').oninput = function() {
    document.getElementById('llmTempVal').textContent = this.value;
};

// --- LLM Provider Toggle ---
function setProvider(provider) {
    document.getElementById('btnAnthropic').className = provider === 'anthropic' ? 'active' : '';
    document.getElementById('btnOllama').className = provider === 'ollama' ? 'active' : '';
    document.getElementById('anthropicConfig').style.display = provider === 'anthropic' ? 'block' : 'none';
    document.getElementById('ollamaConfig').style.display = provider === 'ollama' ? 'block' : 'none';
}

// --- Toast ---
function showToast(msg, type) {
    const el = document.createElement('div');
    el.className = 'toast ' + type;
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 3000);
}

// --- Build config from UI ---
function buildConfig() {
    const ports = {};
    document.querySelectorAll('.port-card').forEach(card => {
        const letter = card.querySelector('.port-type').dataset.port;
        const type = card.querySelector('.port-type').value;
        const role = card.querySelector('.port-role').value;
        if (type) {
            ports[letter] = { type: type, role: role || type };
        }
    });

    const driving = {};
    const fl = document.getElementById('driveFrontLeft').value;
    const fr = document.getElementById('driveFrontRight').value;
    const rl = document.getElementById('driveRearLeft').value;
    const rr = document.getElementById('driveRearRight').value;
    if (fl) driving.front_left = fl;
    if (fr) driving.front_right = fr;
    if (rl) driving.rear_left = rl;
    if (rr) driving.rear_right = rr;

    const reversed = [];
    document.querySelectorAll('.reversed-port:checked').forEach(cb => {
        reversed.push(cb.value);
    });
    if (reversed.length > 0) driving.reversed = reversed;

    const provider = document.getElementById('btnOllama').className.includes('active') ? 'ollama' : 'anthropic';
    const llm = {
        provider: provider,
        max_tokens: parseInt(document.getElementById('llmMaxTokens').value),
        temperature: parseFloat(document.getElementById('llmTemp').value)
    };

    if (provider === 'anthropic') {
        llm.model = document.getElementById('anthropicModel').value;
    } else {
        llm.model = document.getElementById('ollamaModel').value;
        llm.url = document.getElementById('ollamaUrl').value;
    }

    return {
        ports: ports,
        driving: driving,
        safety: {
            max_speed: parseInt(document.getElementById('maxSpeed').value),
            default_speed: parseInt(document.getElementById('defaultSpeed').value),
            min_battery_pct: 10
        },
        llm: llm
    };
}

// --- Save config ---
async function saveConfig() {
    const config = buildConfig();
    const res = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
    });
    if (res.ok) {
        showToast('Configuration saved!', 'success');
    } else {
        showToast('Error saving configuration', 'error');
    }
}

// --- Profile Templates ---
const templates = {
    patrol: {
        name: 'patrol',
        description: 'Security patrol robot - drives around, detects obstacles',
        behavior: 'You are a security patrol robot.\n\n- Patrol forward at moderate speed\n- Stop and alert when obstacles are closer than 200mm\n- Turn away from obstacles\n- Show FALSE icon on detection, HAPPY during normal patrol\n- Use sound for alarm (800Hz)'
    },
    dog: {
        name: 'dog',
        description: 'Robot puppy - playful, curious, happy',
        behavior: 'You are a playful robot puppy!\n\n- HAPPY: Show HAPPY, drive around a bit\n- CURIOUS: When something is close (< 300mm), move slowly toward it\n- PLAYFUL: On tapped gesture, spin and beep\n- SCARED: On shake, reverse backward, show SAD\n- SLEEPING: When nothing happens, stop motors, show PAUSE'
    },
    explorer: {
        name: 'explorer',
        description: 'Explorer - systematically maps the surroundings',
        behavior: 'You are a systematic explorer robot.\n\n- Drive forward until you find an obstacle\n- Turn 90 degrees and continue\n- Keep track of direction via IMU heading\n- Try to cover as much area as possible\n- Show ARROW_UP when driving forward, ARROW_LEFT/RIGHT when turning'
    },
    dancer: {
        name: 'dancer',
        description: 'Dancer - moves rhythmically and playfully',
        behavior: 'You are a dance bot!\n\n- Drive in circles, spin, and zig-zag\n- Vary between fast and slow movements\n- Use sound for rhythm (short beeps in patterns)\n- Show HEART on display\n- React to IMU movement with more energetic dancing'
    },
    shy: {
        name: 'shy',
        description: 'Shy robot - afraid of anything that approaches',
        behavior: 'You are a shy, nervous robot.\n\n- Stand still and show PAUSE by default\n- When distance sensor detects something (< 400mm): reverse slowly backward\n- The closer something is, the faster you reverse\n- Beep softly (low frequency, 200Hz) when scared\n- Show SAD when something is close, HAPPY when the coast is clear'
    },
    custom: {
        name: '',
        description: '',
        behavior: ''
    }
};

function loadTemplate(key) {
    const t = templates[key];
    document.getElementById('profileName').value = t.name;
    document.getElementById('profileDesc').value = t.description;
    document.getElementById('profileBehavior').value = t.behavior;

    // Highlight selected template
    document.querySelectorAll('.template-card').forEach(c => c.classList.remove('selected'));
    event.currentTarget.classList.add('selected');
}

// --- Save Profile ---
async function saveProfile() {
    const name = document.getElementById('profileName').value.trim().toLowerCase().replace(/\s+/g, '_');
    const desc = document.getElementById('profileDesc').value;
    const behavior = document.getElementById('profileBehavior').value;

    if (!name) {
        showToast('Enter a profile name', 'error');
        return;
    }
    if (!behavior) {
        showToast('Describe the behavior', 'error');
        return;
    }

    const res = await fetch('/api/profiles', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            name: name,
            description: desc,
            behavior: behavior
        })
    });

    if (res.ok) {
        showToast('Profile "' + name + '" saved!', 'success');
        setTimeout(() => location.reload(), 500);
    } else {
        const data = await res.json();
        showToast(data.error || 'Error', 'error');
    }
}

// --- Delete Profile ---
async function deleteProfile(name) {
    if (!confirm('Delete profile "' + name + '"?')) return;

    const res = await fetch('/api/profiles/' + name, { method: 'DELETE' });
    if (res.ok) {
        const el = document.getElementById('profile-' + name);
        if (el) el.remove();
        showToast('Deleted!', 'success');
    }
}

// --- Robot Control ---
async function startRobot(profile) {
    // Save config first
    await saveConfig();

    const res = await fetch('/api/robot/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile: profile })
    });

    if (res.ok) {
        showToast('Robot started with profile: ' + profile, 'success');
        updateStatus(true);
    } else {
        const data = await res.json();
        showToast(data.error || 'Could not start', 'error');
    }
}

async function stopRobot() {
    const res = await fetch('/api/robot/stop', { method: 'POST' });
    if (res.ok) {
        showToast('Robot stopped', 'success');
        updateStatus(false);
    }
}

function updateStatus(running) {
    const badge = document.getElementById('robotStatus');
    const stopBtn = document.getElementById('stopGroup');
    if (running) {
        badge.className = 'status-badge running';
        badge.textContent = 'Running';
        stopBtn.style.display = 'flex';
    } else {
        badge.className = 'status-badge stopped';
        badge.textContent = 'Stopped';
        stopBtn.style.display = 'none';
    }
}

// Poll robot status
async function checkStatus() {
    try {
        const res = await fetch('/api/robot/status');
        const data = await res.json();
        updateStatus(data.running);
    } catch (e) {}
}

setInterval(checkStatus, 3000);
checkStatus();

// Auto-save config on any change
document.querySelectorAll('select, input[type="range"]').forEach(el => {
    el.addEventListener('change', () => {
        clearTimeout(window._saveTimer);
        window._saveTimer = setTimeout(saveConfig, 1000);
    });
});

document.querySelectorAll('.port-role').forEach(el => {
    el.addEventListener('input', () => {
        clearTimeout(window._saveTimer);
        window._saveTimer = setTimeout(saveConfig, 1500);
    });
});
