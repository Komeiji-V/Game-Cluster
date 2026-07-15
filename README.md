# 小游戏集群 (Game Cluster)

> 🎮 一个面向多人在线迷你游戏的轻量级网页平台  
> 🧪 非计算机专业新手的第一次 Vibe Coding 尝试

本项目通过与 AI（OpenCode）对话逐步搭建完成，从架构设计到安全审计全程 AI 辅助。旨在探索"自然语言驱动开发"（Vibe Coding）的可能性和边界。

---

## 功能

- **用户系统** — 邮箱注册/登录，支持 SMTP 验证（可选）
- **实时排行榜** — WebSocket + Redis Pub/Sub，分数实时刷新
- **模块化游戏** — 上传 ZIP 包即上线，框架自动注册
- **游客模式** — 未登录也能玩，提交分数时提示登录
- **日夜间模式** — 页面全局切换，自动持久化
- **后台管理** — SMTP 设置、游戏上传/删除、用户管理、站点标题/图标/主题色
- **排行榜分层** — 游戏可独立排行或计入总分（`counts_toward_total`），防止刷分游戏霸榜
- **分数 API** — 供 iframe 嵌入外部网站的个人分数卡片，支持 `?w=300&h=400` 参数自定义尺寸
- **SMTP 测试** — 管理面板内置发送测试邮件的功能
- **安全加固** — Cookie `secure`/`sameSite` 标志、路径穿越防护、XSS 修复、交互式管理员密码输入

---

## 内置游戏

| 游戏 | 类型 | 操作 |
|------|------|------|
| 经典贪吃蛇 🐍 | 穿墙模式 | 方向键/WASD |
| 赛博木鱼 🪵 | 休闲积累 | 鼠标点击/空格 |

DLC 游戏（需手动上传）：
- **俄罗斯方块** — 见 `tetris.zip`（在 Releases 中下载）

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11 + FastAPI |
| ORM | SQLAlchemy 2.0 (async) |
| 数据库 | MySQL 8.0 |
| 缓存 | Redis 7 |
| 前端 | Jinja2 + Bootstrap 5 + 原生 JavaScript |
| 实时 | WebSocket (Starlette) |
| 部署 | Docker + Docker Compose |

---

## 快速开始

### 前置条件

- MySQL 8.0（已创建 `gamecluster` 数据库）
- Redis 7（运行中）
- Docker

### 配置 `.env`

```env
SECRET_KEY=请生成随机字符串替换
MYSQL_HOST=你的MySQL地址
MYSQL_PORT=3306
MYSQL_DATABASE=gamecluster
MYSQL_USER=gamecluster
MYSQL_PASSWORD=你的MySQL密码
REDIS_HOST=你的Redis地址
REDIS_PORT=6379
REDIS_PASSWORD=
```

### 启动

```bash
docker compose up -d
```

### 创建管理员

```bash
docker compose exec app python mkadmin.py
```

脚本会交互式询问用户名、邮箱和密码。第一个创建的用户自动获得管理员权限。登录后请立即进入 `/profile` 修改初始密码。

---

## 项目结构

```
game-cluster/
├── app/
│   ├── main.py              # FastAPI 入口，路由注册，中间件
│   ├── config.py            # 全局配置（环境变量）
│   ├── models/              # SQLAlchemy 模型（User/Score/SiteSettings）
│   ├── routes/              # 路由层
│   │   ├── auth.py          # 注册/登录/邮箱验证
│   │   ├── games.py         # 游戏列表/页面/分数提交
│   │   ├── leaderboard.py   # 排行榜
│   │   ├── admin.py         # 后台管理
│   │   ├── profile.py       # 个人空间
│   │   └── api/
│   │       └── score_query.py  # 外部分数查询 API
│   ├── services/            # 业务逻辑
│   │   ├── auth_service.py  # JWT/密码
│   │   ├── email_service.py # SMTP 邮件
│   │   └── game_loader.py   # 游戏模块扫描/加载
│   ├── ws/
│   │   └── leaderboard.py   # WebSocket 实时推送
│   ├── templates/           # Jinja2 模板（所有页面）
│   ├── static/              # 全局 CSS/JS/上传
│   └── games/               # 游戏模块目录
│       ├── _template/       # 开发模板
│       ├── snake/           # 经典贪吃蛇
│       └── muyu/            # 赛博木鱼
├── docs/
│   └── GAME_DEV_GUIDE.md    # 游戏开发准则
├── docker-compose.yml
├── Dockerfile
├── nginx.conf               # 外部 Nginx 参考配置
├── requirements.txt
└── .env
```

---

## Widget API

供论坛等外部站点通过 iframe 嵌入个人分数卡片。卡片标题在设置站点域名后可点击直达主页。

| API | 说明 | 参数 |
|-----|------|------|
| `GET /api/widget/{game_id}/{user_id}` | 某游戏分数卡片 | `?theme=dark` `?w=300` `?h=400` |
| `GET /api/widget/{game_id}/{user_id}/json` | 同上，JSON 格式 | — |
| `GET /api/ranking/total/{user_id}` | 总分卡片（含各游戏明细） | `?theme=dark` `?w=280` `?h=500` |
| `GET /api/ranking/total/{user_id}/json` | 同上，JSON 格式 | — |

---

## 开发游戏

详细指南：[docs/GAME_DEV_GUIDE.md](docs/GAME_DEV_GUIDE.md)

1. 复制 `app/games/_template/` → 重命名为你的游戏 ID
2. 编辑 `manifest.json`（游戏名称、描述、`counts_toward_total` 是否计入总排行榜）
3. 在 `static/game.js` 中实现游戏逻辑
4. 游戏结束时调用 `window.submitScore(score, gameData)`
5. 打包为 `.zip` → 管理员后台 `/admin/games` 上传

框架自动处理：分数提交、上传动画、页面刷新、排行榜更新。

---

## 关于

**作者：** 非计算机专业的业余爱好者

**开发方式：** 本项目通过与 AI 智能体（OpenCode）的对话完成。从零开始，经历了需求分析 → 架构设计 → 编码实现 → Bug 修复 → 安全审计的完整流程。所有 Python 后端、HTML 模板、JavaScript 游戏逻辑均由 AI 生成，人工负责测试反馈和方向调整。

**投入：** 约 8 小时对话完成核心功能（注册/登录/排行榜/后台管理/2 个内置游戏/俄罗斯方块 DLC），后续约 3 小时调试和完善。

**结论：** Vibe Coding 是可行的，但当前阶段仍需要人工进行需求澄清、逻辑验证和安全审查。AI 善于生成代码，但在上下文保持、代码一致性和安全细节方面仍需人类把关。

---

## 许可证

MIT
