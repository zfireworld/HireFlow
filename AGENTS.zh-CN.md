# 代码库贡献指南

## 项目结构与模块划分

`backend/app/api/` 存放 FastAPI 路由，`entities/` 是 SQLAlchemy 实体，`schemas/` 是请求与结果模型，`services/` 负责业务逻辑，`configuration/` 读取配置文件，`storage/` 管理文件存储，`agents/` 编排 AI 流程，`prompts/` 保存提示词，`clients/` 对接模型和 HiFlow。后端测试位于 `backend/tests/`；`frontend/src/` 是 Vue 3 + TypeScript 界面。

## 构建、测试与开发命令

- `docker compose up -d --build`：构建并启动服务，页面地址为 `http://localhost:8080`。
- `docker compose logs -f backend`：查看后端日志；`docker compose down` 停止服务并保留数据卷。
- 首次使用时复制 `.env.example` 为 `.env`，然后执行 `cd backend; pip install -r requirements.txt; uvicorn app.main:app --reload --port 8000`；按需在配置文件中设置可写的 `DATA_DIR`。
- `cd frontend; npm install; npm run dev`：在 `http://localhost:5173` 启动 Vite，`/api` 代理至 8000 端口。
- `cd frontend; npm run build`：运行 `vue-tsc` 类型检查并生成 `dist/`。
- `python scripts/smoke-test.py`：Docker 服务启动后检查基础 API。

## 代码风格与命名

Python 使用四空格缩进，函数和模块采用 `snake_case`。前端遵循相邻 Vue/TypeScript 文件的格式，变量采用 `camelCase`，组件和类型采用 PascalCase。API 数据契约放在 `backend/app/schemas/`，数据库写入与阶段流转放在 `services/recruitment.py`，外部请求放在 `clients/`。仓库未配置统一格式化或 lint 工具；提交前运行前端类型检查。

## 测试要求

在 `backend/` 运行 `python -m pytest -q`。Pytest 使用 `test_*.py` 文件和 `test_*` 函数；配置测试位于 `test_configuration.py`。`conftest.py` 使用临时配置文件和数据库，不读取项目配置；当前没有覆盖率门槛。

根据仓库使用者的偏好，不使用 Playwright 工作流。

## 提交与拉取请求

当前目录没有 Git 历史，无法确认既有提交格式。建议用简短祈使句概括变更，例如 `Add review validation for interview dates`。拉取请求应说明行为变化、列出已运行的检查、关联相关议题；界面变更请附截图。

## 安全与配置

从 `.env.example` 复制生成 `.env`，不要提交 API 密钥或 Webhook 地址。页面传入的模型密钥仅用于当前请求，不得写入数据库或 LangGraph 状态。仅使用虚构或脱敏简历。本 MVP 缺少认证和生产级文件防护，不应公开部署或处理未经授权的候选人资料。
