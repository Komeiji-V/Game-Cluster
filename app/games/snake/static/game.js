let canvas, ctx, hud;
let snake, food, direction, nextDirection;
let score, gameRunning, gameLoop, speed;
const GRID = 20, COLS = 40, ROWS = 25, INITIAL_SPEED = 110;

function isDark() { return document.documentElement.getAttribute('data-theme') === 'dark'; }
function getCanvasBg() { return isDark() ? '#0a0a1a' : '#e8e8f0'; }
function getGridColor() { return isDark() ? 'rgba(255,255,255,.04)' : 'rgba(0,0,0,.05)'; }

function initGame(containerId) {
    var container = document.getElementById(containerId);
    if (!container) return;
    container.style.position = 'relative';
    container.innerHTML = '<canvas id="snake-canvas" width="' + (GRID * COLS) + '" height="' + (GRID * ROWS) + '"></canvas>'
        + '<div id="snake-hud">得分：<b>0</b> &nbsp;|&nbsp; 按 <b>方向键</b> 或 <b>WASD</b> 开始</div>'
        + '<div id="snake-overlay" style="display:none;position:absolute;inset:0;background:rgba(0,0,0,.6);backdrop-filter:blur(3px);align-items:center;justify-content:center;flex-direction:column;border-radius:12px;z-index:10;">'
        + '<div style="text-align:center;color:#fff;">'
        + '<p style="font-size:1.5rem;font-weight:900;margin:0 0 .3rem 0;">游戏结束</p>'
        + '<p style="color:var(--acc);font-size:2rem;font-weight:900;margin:0 0 1rem 0;" id="overlay-score">0</p>'
        + '<button class="btn btn-primary btn-lg" onclick="restartGame()">重新游戏</button>'
        + '</div></div>';
    canvas = document.getElementById('snake-canvas');
    ctx = canvas.getContext('2d');
    hud = document.getElementById('snake-hud');
    document.addEventListener('keydown', handleKey);

    var observer = new MutationObserver(function() { if (ctx) draw(); });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });

    initState();
    draw();
}

function initState() {
    var sx = Math.floor(COLS / 4), sy = Math.floor(ROWS / 2);
    snake = [{x:sx,y:sy},{x:sx-1,y:sy},{x:sx-2,y:sy}];
    direction = {x:1,y:0};
    nextDirection = {x:1,y:0};
    score = 0;
    gameRunning = false;
    placeFood();
}
function placeFood() {
    var fx, fy;
    do { fx = Math.floor(Math.random() * COLS); fy = Math.floor(Math.random() * ROWS); }
    while (snake.some(function(s) { return s.x === fx && s.y === fy; }));
    food = {x:fx, y:fy};
}
function isModalOpen() {
    var m = document.getElementById('login-modal');
    return m && m.style.display === 'flex';
}
function getOverlay() { return document.getElementById('snake-overlay'); }
function isDead() { var o = getOverlay(); return o && o.style.display === 'flex'; }

function handleKey(e) {
    if (isDead()) return;
    var valid = ['ArrowUp','ArrowDown','ArrowLeft','ArrowRight','w','a','s','d','W','A','S','D'];
    if (valid.indexOf(e.key) === -1) return;
    e.preventDefault();
    if (isModalOpen()) return;
    var newDir;
    switch(e.key) {
        case 'ArrowUp': case 'w': case 'W': newDir = {x:0,y:-1}; break;
        case 'ArrowDown': case 's': case 'S': newDir = {x:0,y:1}; break;
        case 'ArrowLeft': case 'a': case 'A': newDir = {x:-1,y:0}; break;
        case 'ArrowRight': case 'd': case 'D': newDir = {x:1,y:0}; break;
    }
    if (!gameRunning) { startGame(); return; }
    if (direction.x === -newDir.x && direction.y === -newDir.y) return;
    nextDirection = newDir;
}
function startGame() {
    if (gameLoop) clearInterval(gameLoop);
    initState();
    gameRunning = true;
    speed = INITIAL_SPEED;
    updateHUD();
    gameLoop = setInterval(tick, speed);
}
function tick() {
    if (!gameRunning) return;
    direction = Object.assign({}, nextDirection);
    var head = snake[0];
    var newHead = {x: head.x + direction.x, y: head.y + direction.y};
    if (newHead.x < 0) newHead.x = COLS - 1;
    else if (newHead.x >= COLS) newHead.x = 0;
    if (newHead.y < 0) newHead.y = ROWS - 1;
    else if (newHead.y >= ROWS) newHead.y = 0;
    if (snake.some(function(s) { return s.x === newHead.x && s.y === newHead.y; })) { return endGame(); }
    snake.unshift(newHead);
    if (newHead.x === food.x && newHead.y === food.y) {
        score += 10 + Math.floor(snake.length / 5);
        placeFood();
        if (speed > 50) speed -= 1;
        clearInterval(gameLoop);
        gameLoop = setInterval(tick, speed);
    } else { snake.pop(); }
    draw();
    updateHUD();
}
function draw() {
    ctx.fillStyle = getCanvasBg();
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = getGridColor();
    ctx.lineWidth = .5;
    var i;
    for (i = 0; i < COLS; i++) { ctx.beginPath(); ctx.moveTo(i * GRID, 0); ctx.lineTo(i * GRID, canvas.height); ctx.stroke(); }
    for (i = 0; i < ROWS; i++) { ctx.beginPath(); ctx.moveTo(0, i * GRID); ctx.lineTo(canvas.width, i * GRID); ctx.stroke(); }
    ctx.fillStyle = '#f97316';
    ctx.beginPath();
    ctx.arc(food.x * GRID + GRID/2, food.y * GRID + GRID/2, GRID/2 - 2, 0, Math.PI * 2);
    ctx.fill();
    snake.forEach(function(seg, i) {
        ctx.fillStyle = 'rgba(108,92,231,' + (1 - (i / snake.length) * .6) + ')';
        ctx.fillRect(seg.x * GRID + 1, seg.y * GRID + 1, GRID - 2, GRID - 2);
    });
}
function updateHUD() {
    if (hud) hud.innerHTML = '得分：<b>' + score + '</b> &nbsp;|&nbsp; 长度：<b>' + snake.length + '</b>';
}
function endGame() {
    gameRunning = false;
    clearInterval(gameLoop);
    gameLoop = null;
    var finalScore = score;
    if (hud) hud.innerHTML = '游戏结束！得分：<b>' + finalScore + '</b>';
    var o = getOverlay();
    if (o) {
        document.getElementById('overlay-score').textContent = finalScore;
        o.style.display = 'flex';
    }
    draw();
}

function restartGame() {
    if (typeof window.submitScore === 'function') {
        window.submitScore(score, {length: snake.length});
    }
}