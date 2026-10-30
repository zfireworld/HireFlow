# HireFlow AI — Docker 可部署的招聘流程自动化 MVP

使用 **Vue 3 + TypeScript + Element Plus + ECharts / FastAPI + SQLAlchemy + SQLite / LangChain + LangGraph**。模型通过 OpenAI 兼容接口接入；真实企业微信机器人暂时用 Web 聊天页面模拟。支持简历提取、AI 结构化招聘事件、状态机、多轮面试、人工审核和事件同步。

## Docker Compose 启动（Windows 也可）

1. 安装并运行 Docker Desktop（WSL 2 引擎），确认 `docker compose version` 可用。
2. 在项目根目录将 `.env.example` 复制为 `.env`（已有文件不要覆盖），按需填写模型配置。Compose 将配置文件只读挂载给后端；`DATA_DIR=./data` 对应容器的数据卷。
3. PowerShell / 终端执行：

   ```bash
   docker compose up -d --build
   ```

4. 浏览器打开 **http://localhost:8080**；健康检查为 **http://localhost:8080/api/v1/health**，Swagger 文档为 **http://localhost:8080/docs**。容器端口在 `docker-compose.yml` 中设置，旧配置项 `WEB_PORT` 不再生效。
5. 查看日志：`docker compose logs -f backend`；停止：`docker compose down`。数据存储在命名卷 `hireflow_data`，重启不会清空。**不要运行 `docker compose down -v`，除非要彻底删掉业务数据。**

## AI 模式

- **`AI_MODE=auto`（默认）**：配置 `MODEL_API_KEY` 时使用服务器模型；没有 Key 时使用明确标注的**规则演示模式**。
- **`AI_MODE=model`**：使用 `.env` 中的模型名称和接口地址；无需认证的兼容服务可将 Key 留空。
- **`AI_MODE=demo`**：仅使用规则提取，适合无联网环境演示固定测试流程。规则不能理解任意自由语言，必须使用明确的招聘阶段、岗位与日期。

后端直接读取项目根目录 `.env`，不读取同名进程环境变量，也不展开 `${变量名}`；缺少文件时使用内置默认值。`DATA_DIR` 相对后端目录解析；修改文件后重启后端。`QWEN_*` 和 `AI_MODE=qwen` 仍可兼容旧配置，新配置使用 `MODEL_NAME`、`MODEL_BASE_URL`、`MODEL_API_KEY`。

页面右上角“模型设置”可选择**规则演示**、**服务器配置**或**自定义模型**。自定义模式填写服务商提供的 OpenAI 兼容接口地址、模型名称和 API Key（无需认证时可留空），点击“测试模型连接”发送短生成请求。请求级配置仅保存在页面内存，刷新后需重新填写；远程地址携带 Key 时须使用 HTTPS。连通成功只验证接口可生成文本，招聘评估仍需检查 JSON 格式、上下文限制和内容质量。非 OpenAI 兼容的原生协议需要另外开发适配器。

## 建议演示步骤（使用虚构简历）

1. 在聊天页面上传一份**可提取文字**的 PDF/DOCX，包含 `姓名：张晨`、`岗位：Python后端工程师`、`技能：Python、FastAPI、SQL`。填写消息“这是张晨的简历”并发送；前往“简历评估”核对和修改参考信息，选择“待定”并确认，建立候选人和岗位申请。
2. 从左边候选人列表进入详情或在聊天页选择该申请，发送 `HR初筛评价：技术经验不错，建议面试`，状态更新至一面待安排。
3. 选择该申请并发送 `安排一面，2026-11-02 15:00，面试官李工`，状态变为一面待进行。
4. 在“候选人管理 → 面试记录”中找到一面待进行的记录，点击“上传文字”，选择 `examples/虚构面试_张晨_一面.txt`。默认规则演示模式会生成非 AI 的主题和发言统计；可在页面右上角切换模型配置。此时可先查看参考意见，再按下一步选择如何推进。
5. 选择该申请并发送 `一面结束，Python基础扎实，一面通过，安排二面`，新建事件，状态为二面待安排。
6. 在看板查看阶段变化，详情页查看一面记录。再提交一条缺少具体日期的一面安排，将进入人工审核；补充明确日期后批准。
7. 重试相同 `external_message_id`，API 返回 duplicate 而不是重复插入（Web 前端每次发送新建 ID，需通过 API 客户端验证此用例）。

**特别提示：** 面试状态只有已安排该轮时才能提交反馈；如果只有面试评价没有明确通过结论，停在“待反馈”。

## 人工维护候选人

在“候选人管理”中点击“新建候选人 / 申请”，选择已有候选人或填写新人资料，并选择或输入岗位。建档后点击“简历”，可上传 UTF-8 TXT、可提取文字的 PDF / DOCX，或直接填写文字简历；简历按候选人保存，在详情中查看和下载，同一候选人的多份岗位申请共享简历。

在申请行点击“初筛”，填写评价并选择待定、淘汰或进入一面。进入一面后，点击“安排面试”，填写时间和面试官；面试后点击“记录反馈”，填写评价并选择待定、淘汰或通过。待定后的评价和结论可继续通过“记录反馈”修改；通过后进入下一轮待安排。三面通过后，可在申请行依次确认接受 Offer 和入职。面试记录页可修改已安排的时间、面试官，以及已完成面试的评价。阶段变更按现有规则校验并记录事件，不需要配置模型。

## 面试全程文字与 AI 总结

面试安排完成后，在“候选人管理 → 面试记录”的待进行面试行上传可提取文字的 `.txt`（UTF-8）、`.pdf` 或 `.docx` 文件，也可从候选人详情中的待进行面试上传。系统保存完整文字，并让 Qwen 提取候选人、岗位、轮次、面试官、时间等基本信息，生成中文总结、讨论主题、有依据的表现、待核实问题和后续事项。点击“查看完整面试文字”可核对原文；再次上传会生成新版本，页面显示最新版本。面试完成或该轮已不处于待进行状态时，不再接受新的文字上传。

规则演示模式无需模型，生成明确标注“非 AI”的发言数量、关键词和候选人原话，不自动评分；模型模式提供具体表现、面试官建议和岗位相关维度的 1–5 分参考评分。评分要求附逐字稿原文依据，缺少依据时不显示分数；面试官可核对和修改。单个文件上限 5 MB，提取文字上限 60,000 字，PDF 上限 25 页。上传后不会自动改变面试结论或阶段；面试官可在详情中修改信息和建议，选择“待定、淘汰、推进”并确认。候选人、岗位和轮次须与关联面试一致；三面选择推进进入 Offer 待处理。

## 简历评估与人工决定

上传简历并发送后，简历 Agent 会提取基本信息、提供岗位相关评价和面试建议。评估生成后显示在“简历评估”页面，面试官可修改后选择“待定、淘汰、进入一面”并确认。待定会建立或关联处于简历筛选阶段的申请，之后可继续选择淘汰或进入一面。评估结果与人工确认结果分别保留；结果和阶段变更会生成事件和同步任务。

简历文件提交使用 `POST /api/v1/resume-assessments` 和确认接口；旧的 `/api/v1/messages` 不再接受 `file_id` 直接建档。新数据库表由后端启动时自动创建。原有聊天文本和待审核任务仍可使用。

## 腾讯文档单向同步

1. 腾讯云 HiFlow 创建一个 **Webhook 触发 → 腾讯在线表格添加一行** 的自动化流程。
2. 表头建议：`event_id, at, candidate_id, application_id, position, event_type, old_stage, new_stage, round_no, decision, operator`。
3. 将 HiFlow Webhook URL 配置为 `.env` 中的 `HIFLOW_WEBHOOK_URL`，重新启动后端。
4. 每次**数据库事务提交成功**后，同步 outbox 会每 20 秒尝试发送，最多指数退避至 1h。接口 `/api/v1/sync/jobs` 可以查看状态；未配置 Webhook 时任务保留为 `pending`。

注意：HiFlow 的具体字段映射需要按连接器界面配置；Webhook 对端不一定支持去重，重试时外部表格可能出现重复事件 ID。正式落地须做外部去重或人工巡检。第一版 **只追加事件流水，不做腾讯文档主表原行更新**。

## 本地开发（非 Docker）

后端目录按职责划分：`app/entities/` 是数据库实体，`app/schemas/` 是请求与结果模型，`app/api/` 是 HTTP 路由，`app/services/` 是业务逻辑，`app/configuration/` 读取配置文件，`app/storage/` 管理文件存储，`app/agents/` 是 AI 流程，`app/prompts/` 是提示词，`app/clients/` 封装模型与 HiFlow 外部调用。启动入口仍为 `app.main:app`。

前端 `src/` 存放页面与组件，`src/types/` 存放共享业务类型，`src/utils/` 存放通用工具。候选人与申请、面试记录统一从“候选人管理”进入。

首次使用时，在项目根目录将 `.env.example` 复制为 `.env`，按需编辑；已有配置不要覆盖。然后启动后端：

```bash
cd backend
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

新终端：

```bash
cd frontend
npm install
npm run dev
```

前端默认 `http://localhost:5173`，由 Vite 将 `/api` 代理到本地 8000。

## 测试

```bash
cd backend
python -m pytest -q
```

测试使用独立的临时配置文件和数据库，不读取项目 `.env`。

## 重要边界和安全提示

- 这是面试用 **MVP**，没有登录、RBAC、HTTPS、杀毒扫描、数据脱敏存储或完备租户隔离。**只使用虚构或已脱敏简历，不要公开到互联网，不要未经授权处理真实候选人数据。** 生产使用前必须加认证授权、访问日志、文件安全、隐私保留及删除、加密、备份、审计。
- 简历支持 UTF-8 TXT 或可复制文字的 PDF / DOCX；扫描 PDF / 图片 OCR 暂未实现；文件上限 5 MB、PDF 25 页。
- 不自动登录或抓取 BOSS 等第三方招聘网站。前端聊天界面可以被未来企业微信消息 Adapter 替换。
- SQLite + 单进程 Uvicorn + SQLite checkpoint 为轻量演示适配，不建议直接作为大规模并发生产部署。
- LangGraph 负责结构化提取、校验分流和可恢复的审核中断；真实数据修改由确定性的 SQLAlchemy 业务层完成。`review_tasks` 保留待审核事件，人工确认后才入库。

## 项目附带资料

- `examples/虚构候选人_张晨_测试简历.docx`：可直接上传的完全虚构 DOCX 简历。
- `examples/虚构面试_张晨_一面.txt`：可上传到一面记录的虚构面试逐字稿。
- `scripts/start-windows.ps1`：Windows PowerShell 一键创建本地 `.env` 并执行 Docker Compose 构建。
- `scripts/smoke-test.py`：容器启动后，执行 `python scripts/smoke-test.py` 检查健康、看板、申请、审核 API。
- `backend/tests/`：核心状态机单元测试，以及需要完整 LangGraph 环境的 API 集成测试。

## 验证记录与局限

模型连通性取决于具体服务商支持的接口和模型能力；请按页面连接测试及 [人工测试说明](docs/人工测试流程说明.md) 验证。HiFlow 和容器部署需在各自可用的环境中验证。
