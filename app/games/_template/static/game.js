/**
 * 小游戏模块开发模板
 *
 * 必须实现：
 *   initGame(containerId) — 在 #game-root 容器内初始化游戏
 *
 * 分数提交（框架自动处理上传动画 + 刷新）：
 *   window.submitScore(score, gameData)
 *     score    : 整数，最终分数
 *     gameData : 可选对象，附加数据（连击数、回放等）
 *
 *   框架行为：
 *     未登录 → 弹出登录/注册提示框
 *     已登录 → 显示 "上传中，请勿刷新或退出..." 遮罩
 *            → 提交分数到服务器
 *            → 成功 → 自动刷新页面显示最新排行榜
 *            → 失败 → 隐藏遮罩，弹出登录提示
 *
 * 示例：
 *   function onGameOver() {
 *     window.submitScore(1500, { maxCombo: 8, clicks: 120 });
 *   }
 *
 * 注意：不要在自己的游戏里调用 location.reload()
 *      框架会在上传成功后自动刷新
 */

let GAME_CONTAINER = null;

function initGame(containerId) {
    GAME_CONTAINER = document.getElementById(containerId);
    if (!GAME_CONTAINER) {
        console.error('Game container not found: ' + containerId);
        return;
    }

    // TODO: Set up your game canvas/UI here
    // Example: Create a canvas
    const canvas = document.createElement('canvas');
    canvas.id = 'game-canvas';
    canvas.width = 800;
    canvas.height = 500;
    canvas.style.maxWidth = '100%';
    canvas.style.display = 'block';
    canvas.style.margin = '0 auto';
    canvas.style.border = '1px solid rgba(255,255,255,.1)';
    canvas.style.borderRadius = '8px';
    canvas.style.background = '#0a0a1a';
    GAME_CONTAINER.innerHTML = '';
    GAME_CONTAINER.appendChild(canvas);

    // TODO: Add game controls/HUD
    const hud = document.createElement('div');
    hud.id = 'game-hud';
    hud.style.textAlign = 'center';
    hud.style.marginTop = '12px';
    hud.style.color = '#aaa';
    hud.innerHTML = 'Press <b>Start</b> to begin!';
    GAME_CONTAINER.appendChild(hud);

    const btn = document.createElement('button');
    btn.className = 'btn btn-primary mt-2';
    btn.textContent = 'Start';
    btn.onclick = startGame;
    GAME_CONTAINER.appendChild(btn);
}

function startGame() {
    const hud = document.getElementById('game-hud');
    if (hud) hud.innerHTML = 'Game started! Score: 0';

    // TODO: Implement your game loop here
    // When game ends:
    //   window.submitScore(finalScore, optionalGameData);
}
