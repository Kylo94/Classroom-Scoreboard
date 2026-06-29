# 课堂记分板 · Classroom Scoreboard

一个轻量的课堂学生记分板 — 按班级管理学生，±1/±5 实时加减分，随机提问，跑马灯高亮，数据可导出 JSON / CSV。

![Tech](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Tech](https://img.shields.io/badge/FastAPI-0.138-009688?logo=fastapi&logoColor=white)
![Tech](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)

## ✨ 功能

- 🏫 多班级管理，班级独立
- ➕➖ 每张学生卡片 `+1 / +5 / -1 / -5` 一键加减分（即时动画，无需刷新）
- ✏️ 铅笔按钮改名（Enter 保存，Esc 取消）
- 🎲 随机提问：老虎机式滚动 + 减速落定，被选中学生卡片获得彩色跑马灯高亮
- 🗄️ 数据管理页：班级总览、统计卡、JSON / CSV 导出
- 🎨 玻璃拟态 UI、渐变光斑、跑马灯边框动画

## 🚀 快速开始

### 本地（需要 [uv](https://docs.astral.sh/uv/)）

```bash
git clone <your-repo-url> scoreboard
cd scoreboard
uv sync                  # 创建虚拟环境并安装依赖
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

打开 http://localhost:8000

### Docker（推荐）

```bash
# 本地构建并运行
docker compose up -d --build

# 或者从 GitHub Container Registry 拉取已发布镜像
docker compose pull && docker compose up -d
```

数据持久化在 `./data/scoreboard.db`（通过 volume 挂载到容器 `/app/data/`）。

镜像地址：`ghcr.io/<你的用户名>/scoreboard`

## 🛠️ 技术栈

| 层 | 选型 |
|---|---|
| Web 框架 | FastAPI |
| 模板 | Jinja2 |
| 数据 | SQLite (单文件) |
| 运行时 | Python 3.12 |
| 依赖管理 | uv (`uv.lock`) |
| 容器化 | Docker 多阶段构建 + docker compose |

## 📂 项目结构

```
.
├── Dockerfile             # 多阶段构建，运行时镜像 ~150MB
├── docker-compose.yml     # 一键启动 + 数据卷
├── .github/workflows/
│   └── docker.yml         # CI: 推 main / tag 自动构建并发布到 ghcr.io
├── main.py                # FastAPI 路由
├── database.py            # SQLite 封装，自启动建表
├── templates/index.html   # 主页面
├── templates/admin.html   # 数据管理页
├── static/                # CSS / JS
├── pyproject.toml
└── uv.lock
```

## ⚙️ 配置

通过环境变量覆盖数据库位置（默认 `./scoreboard.db`）：

```yaml
environment:
  - SCOREBOARD_DB=/app/data/scoreboard.db
```

## 📤 发布到 GitHub + ghcr.io

1. 在 GitHub 上创建一个**空仓库**（不勾选任何初始化选项）。
2. 推代码：

   ```bash
   git init                     # 如果还没初始化
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/<你的用户名>/scoreboard.git
   git push -u origin main
   ```

3. **打开 GHCR 写入权限**：仓库 → Settings → Actions → General
   → Workflow permissions → 选 **"Read and write permissions"** → 保存。

4. 推送后 Actions 自动跑：构建 `linux/amd64` + `linux/arm64` 双架构镜像，推到
   `ghcr.io/<你的用户名>/scoreboard`，并打上 `latest` 标签。

5. 拉取：

   ```bash
   docker pull ghcr.io/<你的用户名>/scoreboard:latest
   ```

如要发版：

```bash
git tag v1.0.0
git push origin v1.0.0
```

会额外打上 `1.0.0`、`1.0` 标签。

## 🧪 API（少数暴露给前端的 JSON 端点）

| 方法 | 路径 | 用途 |
|---|---|---|
| `GET` | `/` | 主页（默认显示第一个班级） |
| `GET` | `/class/{id}` | 指定班级主页 |
| `GET` | `/admin` | 数据管理页 |
| `GET` | `/admin/export/json` | 下载 JSON 备份 |
| `GET` | `/admin/export/csv` | 下载 CSV 表格 |
| `POST` | `/classes/{id}/students/{sid}/score` | JSON：增减分 |
| `POST` | `/classes/{id}/students/{sid}/rename` | JSON：改名 |

## 📝 许可

MIT