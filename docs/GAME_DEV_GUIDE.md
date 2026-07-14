# 小游戏开发准则

欢迎为「小游戏集群」开发新游戏！本指南涵盖从零到上传的全部流程。

---

## 1. 文件结构

每个游戏是一个文件夹，放在 `app/games/` 下：

```
your-game/
├── manifest.json       # 游戏元数据（必需，JSON格式）
├── template.html       # 游戏页面 HTML 片段（必需）
└── static/
    ├── game.js         # 游戏前端逻辑（必需）
    ├── game.css        # 游戏样式（可选但推荐）
    └── *.png / *.mp3   # 图片、音频等资源（可选）
```

**注意**：文件夹名必须与 `manifest.json` 中的 `game_id` 一致。

---

## 2. manifest.json

```json
{
    "game_id": "your_game_id",
    "name": "你的游戏名称",
    "description": "游戏的简短描述，将显示在游戏大厅卡片上",
    "version": "1.0",
    "author": "你的名字"
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `game_id` | ✅ | 唯一标识符，只能包含小写英文字母、数字和下划线 |
| `name` | ✅ | 游戏的中文名称 |
| `description` | 否 | 简介文字，留空则显示空 |
| `version` | 否 | 版本号，默认为 `1.0` |
| `author` | 否 | 作者名，默认为 `unknown` |

---

## 3. template.html

只需一个 `id="game-root"` 的容器，框架会在这个容器内加载你的游戏：

```html
<!-- 如果有自定义样式，先引用 -->
<link rel="stylesheet" href="/games/static/your_game_id/static/game.css">

<!-- 游戏容器：框架会在此 div 内调用你的 initGame 函数 -->
<div id="game-root" style="display:flex;align-items:center;justify-content:center;min-height:500px;width:100%;">
    <p style="color:var(--txt-2);">加载中...</p>
</div>

<!-- 框架自动：等待 DOM 加载完成后调用你的 initGame 函数 -->
<script>
document.addEventListener('DOMContentLoaded', function() {
    if (typeof initGame === 'function') { initGame('game-root'); }
});
</script>
```

**关键点**：
- 容器必须是 `<div id="game-root">`
- `initGame('game-root')` 是框架约定的入口函数名
- CSS 文件路径格式：`/games/static/{game_id}/static/game.css`

---

## 4. game.js 核心 API

### 4.1 必须实现的函数

```javascript
/**
 * 框架入口函数
 * @param {string} containerId - 容器元素 ID，固定为 'game-root'
 *
 * 在此函数内完成：
 *   1. 获取容器元素：document.getElementById(containerId)
 *   2. 在容器内创建游戏 UI（Canvas、按钮、HUD 等）
 *   3. 绑定键盘/鼠标事件监听
 *   4. 调用初始化状态（如 initState()）
 *   5. 调用首次渲染（如 draw()）
 */
function initGame(containerId) {
    var container = document.getElementById(containerId);
    if (!container) return;

    // 示例：创建 Canvas 元素
    container.innerHTML = '<canvas id="my-canvas" width="400" height="600"></canvas>'
        + '<div id="my-hud">分数：<b>0</b></div>';

    // 获取引用、绑定事件、初始化...
    canvas = document.getElementById('my-canvas');
    ctx = canvas.getContext('2d');
    document.addEventListener('keydown', handleKey);
    initState();
    draw();
}
```

### 4.2 框架提供的能力

#### 提交分数 `window.submitScore(score, gameData)`

```javascript
// 游戏结束时调用，框架自动处理上传动画 + 页面刷新
window.submitScore(分数, 附加数据);

// 示例：
function gameOver() {
    hud.innerHTML = '游戏结束！得分：<b>' + score + '</b>';
    window.submitScore(score, {
        lines: 15,      // 消除行数
        level: 3,       // 游戏等级
        maxCombo: 8     // 最大连击
    });
}
```

**框架自动处理的完整流程**：

| 情况 | 框架行为 |
|------|---------|
| 用户已登录 | 显示 "上传数据中 ⏳" 旋转遮罩 → 提交分数 → 页面自动刷新 |
| 用户未登录 | 弹出登录/注册提示框，用户可选择登录或继续以游客身份游玩 |
| 网络错误 | 隐藏遮罩，不刷新页面，玩家可以重试 |

**❌ 不要自己调用 `location.reload()`！** 框架在提交成功后会自动刷新页面。
**❌ 不要在 `gameData` 中放入函数、DOM 元素或循环引用。** 它必须是纯 JSON 对象。

#### 日夜模式

框架通过 `<html data-theme="light">` 或 `<html data-theme="dark">` 控制主题。CSS 变量自动切换。

```javascript
// 检测当前主题
var isDark = document.documentElement.getAttribute('data-theme') === 'dark';

// Canvas 游戏中根据主题选色
var bgColor = isDark ? '#0a0a1a' : '#e8e8f0';
var gridColor = isDark ? 'rgba(255,255,255,.04)' : 'rgba(0,0,0,.06)';

// 监听主题切换（Canvas 游戏需要重绘）
new MutationObserver(function() {
    draw();  // 重绘整个画面
}).observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['data-theme']
});
```

**可用 CSS 变量**（在 CSS 文件或内联样式中使用）：

```css
var(--acc)       /* 主题色 #f97316 */
var(--txt)       /* 主文字色 */
var(--txt-2)     /* 次要文字色 #6b7280 */
var(--border)    /* 边框色 #e5e7eb */
var(--bg)        /* 页面背景色 */
```

#### 排行榜

每个游戏页面下方**自动显示该游戏的前 10 名排行榜**。你唯一需要做的就是在游戏结束时调用 `window.submitScore()`。框架自动处理排名更新。

#### 外部 API（用于 iframe 嵌入论坛）

| API | 说明 |
|-----|------|
| `GET /api/widget/{game_id}/{user_id}` | HTML 卡片，显示该用户在该游戏的最高分和排名 |
| `GET /api/widget/{game_id}/{user_id}/json` | JSON 格式，同上 |
| `GET /api/ranking/total/{user_id}` | HTML 总分卡片，显示用户在所有游戏中的表现 |
| `GET /api/ranking/total/{user_id}/json` | JSON 格式，同上 |

---

## 5. gameData 规范

`gameData` 是可选的附加数据对象，存储在数据库 `scores` 表的 `game_data` JSON 字段中。建议包含：

```json
{
    "lines": 10,       // 俄罗斯方块：消除行数
    "level": 3,        // 游戏等级
    "maxCombo": 8,     // 最大连击
    "clicks": 120,     // 赛博木鱼：点击次数
    "length": 15       // 贪吃蛇：长度
}
```

排行榜按 `score` 字段排序，`gameData` 仅供展示和存档。

---

## 6. 打包上传（管理员操作）

1. 确认文件齐全：`manifest.json`、`template.html`、`static/game.js`（以及可选的 `game.css` 和资源文件）
2. 将游戏文件夹压缩为 `.zip`：
   ```bash
   Compress-Archive -Path your-game\* -DestinationPath your-game.zip
   ```
3. 登录管理员后台 → `/admin/games` → 上传 ZIP
4. 框架自动解压、验证文件完整性、注册到数据库

**验证标准**：
- ZIP 包内必须包含 `manifest.json`、`static/game.js`、`template.html`
- `game_id` 不能与已有游戏重复
- `game_id` 只能包含小写字母、数字和下划线

---

## 7. 完整示例：俄罗斯方块

```javascript
// ===== static/game.js =====
var canvas, ctx, hud;
var score = 0, gameRunning = false;

function initGame(containerId) {
    var c = document.getElementById(containerId);
    if (!c) return;
    // 创建 Canvas + HUD
    c.innerHTML = '<canvas id="tetris-canvas" width="300" height="600"></canvas>'
        + '<div id="tetris-hud">分数：<b>0</b> &nbsp;|&nbsp; 按方向键开始</div>';
    canvas = document.getElementById('tetris-canvas');
    ctx = canvas.getContext('2d');
    hud = document.getElementById('tetris-hud');
    document.addEventListener('keydown', handleKey);
    // 监听主题变化
    new MutationObserver(function() { draw(); }).observe(
        document.documentElement, { attributes: true, attributeFilter: ['data-theme'] }
    );
    initState();
    draw();
}

function initState() {
    score = 0; gameRunning = false;
    // ... 初始化棋盘、方块等
}

function startGame() { gameRunning = true; /* 启动循环 */ }

function handleKey(e) {
    if (!gameRunning) { startGame(); return; }
    // 处理上下左右、旋转、硬降
}

function gameOver() {
    gameRunning = false;
    hud.innerHTML = '游戏结束！得分：<b>' + score + '</b>';
    // ★ 调用框架提交函数 ★
    window.submitScore(score, { lines: 15, level: 3 });
}

function draw() {
    // 绘制棋盘、当前方块、预览
    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    ctx.fillStyle = isDark ? '#0a0a1a' : '#e8e8f0';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    // ...
}
```

---

## 8. 常见问题

**Q: 游戏能使用第三方库吗？**
A: 可以。把库文件放在 `static/` 目录下，在 `template.html` 中引用即可。

**Q: 分数提交后排行榜不更新？**
A: 检查 `submitScore` 的第一个参数确实是整数，且用户已登录。未登录的用户不会更新排行榜。

**Q: Canvas 游戏在暗色模式下颜色不对？**
A: 使用 MutationObserver 监听 `data-theme` 属性变化，在回调中根据 `isDark` 重选颜色并重绘。

**Q: 提交分数后页面刷新的时机？**
A: 框架在服务器确认分数入库后才触发刷新，不会丢分。
