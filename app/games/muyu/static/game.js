const MERIT_CAP = 100000000;
let svgFish, hud, submitBtn;
let score = 0, combo = 0, maxCombo = 0, totalClicks = 0;
let lastClickTime = 0, gameStarted = false;
let longPressTimer = null, autoClickInterval = null, isLongPressing = false;
let longPressTrackMouse = false;
let meritComplete = false, submitting = false;
let audio = null;
let mouseX = 0, mouseY = 0;
let clickHistory = [];
let autoMode = false, autoSpeed = 500, autoModeInterval = null;
let spaceHeld = false;
const SPEED_OPTIONS = [500, 750, 1000, 1500, 2000];
const COMBO_WINDOW = 1500, LONG_PRESS_MS = 800, AUTO_CLICK_MS = 55;

function isDark() { return document.documentElement.getAttribute('data-theme') === 'dark'; }

async function initGame(containerId) {
    var c = document.getElementById(containerId);
    if (!c) return;
    c.style.overflow = 'hidden';
    c.innerHTML =
        '<div id="muyu-stage" style="text-align:center;padding:30px 0;position:relative;">'
        + '<div id="muyu-area" style="display:inline-block;cursor:pointer;position:relative;z-index:2;">'
        + '<img id="muyu-svg" src="/games/static/muyu/static/fish.png" style="width:250px;height:auto;transition:transform .05s;filter:drop-shadow(0 4px 12px rgba(0,0,0,.2));">'
        + '</div>'
        + '</div>'
        + '<div id="muyu-hud" style="text-align:center;margin-top:12px;font-size:15px;color:var(--txt-2);">'
        + '功德：<b>0</b> &nbsp;|&nbsp; 点击木鱼开始修行'
        + '</div>'
        + '<div style="text-align:center;margin-top:8px;display:flex;gap:6px;justify-content:center;flex-wrap:wrap;">'
        + '<button class="btn btn-sm btn-outline-secondary" id="muyu-submit" onclick="manualSubmit()" style="display:none;">提交功德</button>'
        + '<button class="btn btn-sm btn-outline-secondary" id="muyu-auto" onclick="toggleAuto()">⚡ 自动敲击</button>'
        + '<select id="muyu-speed" class="form-select" style="width:auto;display:none;font-size:.75rem;padding:.2rem .5rem;" onchange="changeSpeed(this.value)">'
        + SPEED_OPTIONS.map(function(s) { return '<option value="'+s+'"'+(s===autoSpeed?' selected':'')+'>'+s+'ms</option>'; }).join('')
        + '</select>'
        + '</div>';

    svgFish = document.getElementById('muyu-svg');
    hud = document.getElementById('muyu-hud');
    submitBtn = document.getElementById('muyu-submit');

    var area = document.getElementById('muyu-area');
    area.addEventListener('mousedown', onPressStart);
    area.addEventListener('mouseup', onPressEnd);
    area.addEventListener('mouseleave', onPressEnd);
    area.addEventListener('touchstart', onPressStart, {passive: false});
    area.addEventListener('touchend', onPressEnd);
    area.addEventListener('touchcancel', onPressEnd);

    audio = new Audio('/games/static/muyu/static/muyu1.mp3');
    audio.preload = 'auto';

    document.addEventListener('mousemove', function(e) { mouseX = e.clientX; mouseY = e.clientY; });
    document.addEventListener('keydown', function(e) {
        if (e.key === ' ' || e.code === 'Space') {
            e.preventDefault();
            if (spaceHeld) return;
            spaceHeld = true;
            var rect = area.getBoundingClientRect();
            onHitByCoord(rect.right - 50, rect.top + 15);
            longPressTimer = setTimeout(function() {
                startAutoClick({ clientX: rect.right - 50, clientY: rect.top + 15 }, false);
            }, LONG_PRESS_MS);
        }
    });
    document.addEventListener('keyup', function(e) {
        if (e.key === ' ' || e.code === 'Space') {
            spaceHeld = false;
            onPressEnd();
        }
    });

    await loadSavedScore();
    updateHUD();
}

async function loadSavedScore() {
    try {
        var r = await fetch('/api/games/muyu/load');
        if (r.ok) {
            var d = await r.json();
            if (d.accumulated_score > 0) {
                score = d.accumulated_score; maxCombo = d.max_combo || 0; totalClicks = d.total_clicks || 0;
                if (d.merit_complete) { meritComplete = true; }
                submitBtn.style.display = 'inline-block'; gameStarted = true;
            }
        }
    } catch (e) {}
}

function playSound() { if (audio) { audio.currentTime = 0; audio.play().catch(function(){}); } }

function onPressStart(e) {
    e.preventDefault();
    mouseX = e.clientX; mouseY = e.clientY;
    onHit(e);
    longPressTimer = setTimeout(function() { startAutoClick(e, true); }, LONG_PRESS_MS);
}
function onPressEnd() {
    clearTimeout(longPressTimer);
    stopAutoClick();
    spaceHeld = false;
}

function startAutoClick(e, trackMouse) {
    isLongPressing = true;
    longPressTrackMouse = trackMouse || false;
    svgFish.style.transform = 'scale3d(0.93,0.93,0.93)';
    autoClickInterval = setInterval(function() { onHit(e); }, AUTO_CLICK_MS);
}
function stopAutoClick() {
    isLongPressing = false;
    clearInterval(autoClickInterval); autoClickInterval = null;
    svgFish.style.transform = 'scale3d(1,1,1)';
}

function onHit(e) {
    var now = Date.now();
    if (now - lastClickTime < COMBO_WINDOW) combo++; else combo = 1;
    if (combo > maxCombo) maxCombo = combo;
    lastClickTime = now;
    totalClicks++;
    clickHistory.push(Date.now());
    if (clickHistory.length > 20) clickHistory.shift();

    if (!meritComplete) {
        if (!gameStarted) { gameStarted = true; submitBtn.style.display = 'inline-block'; }
        score++;
        if (score >= MERIT_CAP) { score = MERIT_CAP; meritComplete = true; stopAutoClick(); }
        if (meritComplete) {
            var banner = document.createElement('div');
            banner.style.cssText = 'position:absolute;inset:0;display:flex;align-items:center;justify-content:center;z-index:10;';
            banner.innerHTML = '<div style="font-size:2rem;font-weight:900;color:#ffd700;text-shadow:0 0 30px rgba(255,215,0,.6);">🌟 功德圆满 🌟</div>';
            document.getElementById('muyu-stage').appendChild(banner);
        }
    }

    playSound();
    svgFish.style.transform = 'scale3d(0.93,0.93,0.93)';
    setTimeout(function() { if (!isLongPressing) svgFish.style.transform = 'scale3d(1,1,1)'; }, 64);

    var area = document.getElementById('muyu-area');
    var rect = area.getBoundingClientRect();
    var useX = (isLongPressing && longPressTrackMouse) ? mouseX : (e && e.clientX ? e.clientX : rect.left + rect.width/2);
    var useY = (isLongPressing && longPressTrackMouse) ? mouseY : (e && e.clientY ? e.clientY : rect.top + rect.height/2);
    var cx = useX, cy = useY;
    var float = document.createElement('span');
    float.className = 'float-text';
    float.textContent = combo >= 30 ? '+'+combo : combo >= 10 ? '+'+combo : '+1';
    float.style.left = (cx - rect.left - 20) + 'px';
    float.style.top = (cy - rect.top - 30) + 'px';
    if (combo >= 30) { float.style.fontSize = '1.8rem'; float.style.color = '#ff4757'; }
    else if (combo >= 10) { float.style.fontSize = '1.6rem'; float.style.color = '#ffa502'; }
    area.appendChild(float);
    setTimeout(function() { float.remove(); }, 700);

    updateHUD();
}

function manualSubmit() {
    if (!gameStarted || submitting) return;
    submitting = true;
    if (typeof window.submitScore === 'function') {
        window.submitScore(score, { clicks: totalClicks, maxCombo: maxCombo, accumulated: true, meritComplete: meritComplete });
    }
}

function onHitByCoord(cx, cy) {
    onHit({ clientX: cx, clientY: cy });
}

function toggleAuto() {
    autoMode = !autoMode;
    stopAutoClick();
    if (autoModeInterval) { clearInterval(autoModeInterval); autoModeInterval = null; }
    var btn = document.getElementById('muyu-auto');
    var sel = document.getElementById('muyu-speed');
    if (autoMode) {
        btn.classList.add('btn-primary'); btn.classList.remove('btn-outline-secondary');
        btn.textContent = '⚡ 已开启';
        sel.style.display = '';
        autoModeInterval = setInterval(function() {
            var area = document.getElementById('muyu-area');
            if (!area) return;
            var rect = area.getBoundingClientRect();
            onHitByCoord(rect.right - 50, rect.top + 15);
        }, autoSpeed);
    } else {
        btn.classList.remove('btn-primary'); btn.classList.add('btn-outline-secondary');
        btn.textContent = '⚡ 自动敲击';
        sel.style.display = 'none';
    }
}

function changeSpeed(v) {
    autoSpeed = parseInt(v);
    if (autoMode) {
        if (autoModeInterval) clearInterval(autoModeInterval);
        autoModeInterval = setInterval(function() {
            var area = document.getElementById('muyu-area');
            if (!area) return;
            var rect = area.getBoundingClientRect();
            onHitByCoord(rect.right - 50, rect.top + 15);
        }, autoSpeed);
    }
}

function updateHUD() {
    if (!hud) return;
    var bpm = 0;
    if (clickHistory.length >= 2) {
        var span = (clickHistory[clickHistory.length - 1] - clickHistory[0]) / 1000;
        if (span > 0) bpm = Math.round((clickHistory.length / span) * 60);
    }
    if (meritComplete) {
        hud.innerHTML = '<span style="color:#ffd700;font-weight:900;">🌟 功德圆满 🌟</span>'
            + ' &nbsp;|&nbsp; 连击：<b>' + combo + '</b>'
            + (maxCombo > 0 ? ' &nbsp;|&nbsp; 最高：<b>' + maxCombo + '</b>' : '')
            + ' &nbsp;|&nbsp; 手速：<b>' + bpm + '</b> BPM'
            + (isLongPressing ? ' <span style="color:#ff6b6b;">⚡自动</span>' : '');
        return;
    }
    hud.innerHTML = '功德：<b>' + score.toLocaleString() + '</b>'
        + ' &nbsp;|&nbsp; 连击：<b>' + combo + '</b>'
        + (maxCombo > 0 ? ' &nbsp;|&nbsp; 最高：<b>' + maxCombo + '</b>' : '')
        + ' &nbsp;|&nbsp; 手速：<b>' + bpm + '</b> BPM'
        + (isLongPressing ? ' <span style="color:#ff6b6b;">⚡自动</span>' : '')
        + (!gameStarted ? ' &nbsp;|&nbsp; 点击木鱼开始修行' : '');
}
