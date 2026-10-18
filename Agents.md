# 苏九学伴 · 项目全景与 Agent 维护规范 (Agents.md)

> **文档定位**：本文档为本项目（苏九学伴 - 苏州市9年级学习助手中台）的统一设计规范与全局上下文约定。无论是 AI Agent 协作、后续代码迭代还是 Bug 修复，所有涉及业务逻辑、防超纲约束、飞书协议、架构接口的调整均以此文档为核心依据。

---

## 一、 项目背景与业务边界（红线约束）

### 1. 目标受众与范围
* **目标群体**：苏州市初中九年级（初三）学生。
* **业务定位**：针对苏州中考备考的智能化学习助手中台。
* **终极原则**：**所有知识检索、题目解答、学情分析必须严格限定在苏州市 9 年级范围之内，坚决杜绝超纲内容。**

### 2. 苏州市初三官方教材版本矩阵（必须严格对齐）
任何生成的解析、引用的例题、提供的公式，必须匹配以下教材版本：
* **数学**：**苏科版**（江苏科技出版社·九年级上/下册）
* **物理**：**苏科版**（江苏科技出版社·九年级物理）
* **英语**：**译林牛津版**（9A、9B）
* **化学**：**沪教版** / 苏州市初中化学主流考查标准
* **语文 / 道德与法治 / 历史**：国家**统编部编版**（九年级）

### 3. 三重防超纲机制（Guardrails）
严禁在题目解答中出现高中或大学知识（如使用导数求二次函数极值、立体几何使用空间向量、使用高中电离平衡等）。
1. **数据层白名单（RAG Data Fence）**：检索库只收录苏州九年级教材知识点切片、近5-10年苏州中考真题及各区（姑苏、园区、新区、吴中、相城、吴江、昆山、常熟、太仓、张家港）一模/二模试卷。
2. **提示词负向约束（Prompt Negative Constraints）**：显式限制模型行为，遇超纲提问主动以“*该知识点超出苏州初三考纲要求……*”进行友好拦截与降级解释。
3. **后置审查与词库熔断（Verifier Judge）**：后置拦截词库（维护在 `backend/guardrail.py` 中），命中高中高频超纲词时强制拦截重构。

---

## 二、 整体技术架构与部署拓扑

```
               ┌───────────────────────────────────────────────┐
               │                 飞书客户端                    │
               │  - 会话机器人（主场景）：@助手 呼出学科导航台 │
               │  - 原生交互卡片 v2：无刷新原地切换学科答疑台  │
               │  - 拍照搜题：发送试卷截图，多模态秒级解析     │
               └───────────────────────┬───────────────────────┘
                                       │ HTTPS (Caddy 自动证书)
                                       ▼
               ┌───────────────────────────────────────────────┐
               │        云服务器 (首尔节点 119.28.155.50)      │
               │  - 反向代理：Caddy (https://dilonclaw.cloud) │
               │  - 后端框架：FastAPI + Python 3.12 (systemd)  │
               │  - 鉴权与资源：飞书开放平台 SDK / HTTPX       │
               └───────────────────────┬───────────────────────┘
                                       │ 直连 Google Gemini API (<50ms)
               ┌───────────────────────▼───────────────────────┐
               │         苏州初三专属 AI 检索与防超纲引擎       │
               │  ① 学科考标知识库 (苏科版/译林版/沪教版切片)   │
               │  ② 4级级联容灾防雪崩大模型矩阵 (Gemini 3.5)    │
               │  ③ 防超纲安全围栏 (Prompt 约束 + 违规词拦截)   │
               │  ④ 规范解题步骤输出 (符合中考阅卷踩分标准)    │
               └───────────────────────────────────────────────┘
```

* **战略重心**：现阶段**全力推进飞书机器人会话（Bot 对话框）与富文本交互卡片**作为核心学习辅导载体；网页端（Web App）暂作次级展示。
* **部署基础设施**：
  * **服务器**：腾讯云海外独立节点（Ubuntu 24.04 LTS，韩国首尔，IP: `119.28.155.50`），网络直连 Google Gemini API，延迟低于 50ms。
  * **反向代理**：Caddy 自动 HTTPS 证书续期，外网域名为 `https://dilonclaw.cloud`。
  * **进程管理**：systemd 服务保活（`feishu-suzhou-study.service`），虚拟环境运行在 `/opt/feishu_study_plam/venv`。
  * **飞书事件回调地址**：`https://dilonclaw.cloud/suzhou/api/feishu/event`
  * **模型与系统监控**：`https://dilonclaw.cloud/suzhou/api/system/model_status`

---

## 三、 代码仓库目录结构规范

```text
feishu_study_plam/
├── Agents.md                 # 【全局核心】项目全景、共通规范、Bug 修正日志
├── README.md                 # 快速上手与操作指引
├── backend/                  # 云服务器后端核心
│   ├── main.py               # FastAPI 主服务与飞书事件网关（会话状态、卡片回调、分流调度）
│   ├── guardrail.py          # 苏州9年级防超纲引擎（正负向双重审查、提示词围栏）
│   ├── card_builder.py       # 飞书原生交互卡片 (Interactive Card v2) 构造器（学科导航台、专属工作台、答疑卡）
│   ├── knowledge_db.py       # 苏州初三本地考标知识库（物理/化学/英语/语文重点）
│   ├── llm_provider.py       # 大模型适配调度引擎（Gemini 3.5 旗舰矩阵、四级级联容灾保底）
│   ├── feishu_client.py      # 飞书开放平台客户端（Token 缓存、卡片就地刷新、图片资源下载）
│   └── requirements.txt      # 后端核心依赖清单
├── frontend/                 # 飞书工作台内嵌网页前端 (暂时挂起)
│   └── welcome.html          # 欢迎主页
└── feishu_cards/             # 飞书原生交互卡片 JSON
    └── welcome_card.json     # 欢迎交互卡片模板
```

---

## 四、 共通约定与设计规范 (Common Conventions)

### 1. API 接口响应规范 (API Response Format)
所有后端业务接口均应统一返回符合如下规范的 JSON 格式：
```json
{
  "code": 0,                    // 0 为成功，非 0 为具体错误码
  "msg": "success",             // 状态说明
  "data": {},                   // 业务数据负载
  "meta": {
    "scope": "suzhou_grade_9",  // 明确受众范围
    "guardrail_status": "passed"// 防超纲安全审查状态 (passed / blocked / warning)
  }
}
```

### 2. 飞书开放平台对接约定
* **认证方式**：使用自建应用凭证（`app_id` 与 `app_secret`）动态获取 `tenant_access_token`，内存带过期缓存。
* **权限清单**：必须开通 `im:message`、`im:message.p2p_msg:readonly`、`im:message.group_at_msg:readonly` 及 **`im:resource`（获取与上传图片或文件资源）**。
* **URL 规范**：飞书事件订阅 Webhook 必须为通过公网 SSL 验证的合法 `https://` 地址。

### 3. 解题输出格式规范
面向初三学生的解题输出必须结构化，包含三要素：
1. **【考点定位】**：指出对应苏科版/译林版课本的章节或苏州中考题型考点；
2. **【规范步骤】**：符合初中中考评分标准的推导步骤，写明关键定理依据，不跳步、不超纲；
3. **【踩分点与易错点】**：提醒常见丢分陷阱（如检验根、单位、取值范围）。

### 4. 【科目优先选择】高效工作流 (Subject-First Workflow)
为了大幅提升初中生提问与搜题的精准度，采用学科优先会话交互：
1. **呼出导航**：学生在会话中输入 `@助手` 或 `菜单` / `科目`，呈现 6 大学科按钮（数学、物理、化学、英语、语文、道法历史）；
2. **就地切换工作台**：点击学科按钮，卡片**无刷新原地替换为该学科的专属答疑台**；
3. **状态自动保持**：系统自动记录每位学生当前激活的学科，后续文字提问或图片搜题自动继承该学科的教材版本考标；
4. **一键闭环跳转**：每个答疑结果卡片底部均配置 `🔙 返回本学科工作台` 与 `🔄 更换其他学科` 按钮，随时流畅切换。

### 5. 多模态拍照搜题规范 (Vision OCR & Reasoning)
* 学生将习题截图（几何辅助线题、动态电路图、酸碱盐实验装置）直接发送至飞书对话框；
* 后端通过 `download_image_resource` 拉取二进制原图，送入具备图像解析能力的多模态大模型；
* 注入苏州九年级各学科教材考标约束，模型首先转写题目已知条件与求证，再给出初中解题步骤。

### 6. 模型选型与四级级联容灾防雪崩机制 (Fault-Tolerant Multi-LLM)
* **主力引擎**：采用 Google 最新 **`gemini-3.5-flash`** 系列，兼具秒级响应、超强多模态数理化识图推理与 100 万 Token 超长上下文。
* **级联容灾队列**：
  $$\text{目标模型} \longrightarrow \text{gemini-3.5-flash} \longrightarrow \text{gemini-3.6-flash} \longrightarrow \text{gemini-3.5-flash-lite}$$
* **容灾逻辑**：若任一模型遇到 429 免费层并发超限或 503 偶发拥堵，系统在毫秒级内自动尝试下一顺位，彻底杜绝学生端返回“系统繁忙”。

---

## 五、 Bug 修正与迭代记录 (Changelog & Maintenance Log)

> 当后续修复 Bug、添加新模块或微调考纲规则时，请在此区域持续追加记录，以便回溯和保持上下文一致。

| 日期 | 类型 (Bug / Feature / Rule) | 说明与变更要点 | 涉及文件 |
| :--- | :--- | :--- | :--- |
| 2026-10-13 | Init | 初始化项目架构；确立苏州市9年级专属范围与防超纲机制；设计首版欢迎页与飞书卡片 | `Agents.md`, `backend/`, `frontend/`, `feishu_cards/` |
| 2026-10-13 | Config | 关联 GitHub 远程仓库并完成首次推送同步；记录仓库与部署 Token 配置 | `Agents.md`, `.git/` |
| 2026-10-14 | Feature | 支持飞书会话内 @助手 呼出助学菜单；集成译林版初三英语生词速查与统编版九年级古文古诗速查，支持卡片就地无刷新交互与防超纲拦截 | `backend/main.py`, `backend/card_builder.py`, `backend/knowledge_db.py`, `backend/feishu_client.py` |
| 2026-10-14 | Feature | 全面支持初三数理化题目直接发送截图（拍照搜题）：自动拉取飞书图片资源，利用 Gemini 多模态视觉大模型精准识别几何辅助线与坐标图，按中考规范分步推导与防超纲拦截 | `backend/main.py`, `backend/llm_provider.py`, `backend/feishu_client.py` |
| 2026-10-14 | Feature | 实现【先选科目再答疑】高效工作流与学科答疑台无刷新交互；新增苏科版九年级物理与初三化学核心考点库、高频专题卡片与双引擎路由 | `backend/main.py`, `backend/card_builder.py`, `backend/knowledge_db.py`, `Agents.md` |
| 2026-10-14 | Bugfix | 修复上传数理化习题截图返回“系统繁忙”故障；定位为 Gemini Pro 模型 429 配额限制与旧版别名 503 拥堵；全面升级为 Google 官方推荐的 `gemini-3.5-flash` 旗舰矩阵，并构建 4 级级联容灾防雪崩机制，秒级输出中考答题标准 | `backend/llm_provider.py`, `backend/main.py`, `Agents.md` |
| 2026-10-14 | Feature | 追加初三英语课文划线词组背诵与默写模块：支持课文截图高亮划线识别提取、英->中确认与在线修改释义、卡片/网页逐词翻页默写自测、A4纸规范打印排版（背诵清单与课堂自测卷双模） | `backend/vocab_service.py`, `frontend/vocab_workbench.html`, `backend/card_builder.py`, `backend/llm_provider.py`, `backend/main.py`, `Agents.md` |
| 2026-10-15 | Bugfix | 修复题目（尤其是物理搜题）会不断反复发送答案的问题；定位为飞书 Webhook 3秒超时重发机制与缺少幂等去重所致：引入 `BackgroundTasks` 异步分发大模型解题并即时响应 HTTP 200，新增 `event_id`/`message_id` 双重内存幂等去重器，彻底根除重复推送 | `backend/main.py`, `Agents.md` |
| 2026-10-15 | Feature | 单独隔离并支持【专属背单词机器人（苏九背词伴读）】：重构 `feishu_client` 支持多应用 Token 隔离缓存，新增专属网关 `/api/feishu/vocab_event` 与专属欢迎卡片，学生发图 100% 专精课文划线词汇识别与翻页默写自测 | `backend/feishu_client.py`, `backend/card_builder.py`, `backend/main.py`, `.env`, `Agents.md` |
| 2026-10-18 | Feature | 支持英语课文截图多图连续上传与跨页接缝智能拼接：新增 30 秒防抖聚合队列（连续发图自动重置倒计时并即时反馈接收进度），倒计时结束后多图并发送入 Gemini 3.5 Flash 视觉模型，智能拼接跨图截断短语/长句并自动消除重叠重复，全量输出中考词汇卡片 | `backend/vocab_aggregator.py`, `backend/llm_provider.py`, `backend/main.py`, `backend/card_builder.py`, `Agents.md` |
| 2026-10-18 | Feature | 增加接收图片后【⚡ 立即识别生成】交互按钮：学生上传截图后可选择等待 30 秒自动聚合，也可随时主动点击按钮提前结束倒计时，卡片就地刷新为“正在识别中”，并在后台毫秒级启动多模态提取并回复最终词汇卡 | `backend/card_builder.py`, `backend/vocab_aggregator.py`, `backend/main.py`, `Agents.md` |



---

## 六、 待办事项与路线图 (Roadmap)
- [x] 飞书机器人会话接入与原生互动卡片无刷新联动
- [x] 接入具体大模型接口（Google 最新 Gemini 3.5 旗舰矩阵，支持多模态识图）
- [x] 苏州初三学科考标库构建（苏科版物理、初三化学、译林英语、统编文言）
- [x] 题目截图拍照搜题多模态图文解析
- [x] 先选科目再答疑专属工作台
- [x] 英语课文划线生词短语提取、英->中确认修改、逐词翻页默写与 A4 纸打印导出
- [x] 独立配置专属英语背单词机器人（双机器人架构：全科综合答疑 + 英语划线默写伴读）
- [ ] 接入国内平替大模型接口（DeepSeek R1 / 通义千问等备选）
- [ ] 补充苏科版数学/物理章节知识点知识库 (RAG 向量切片构建)
- [ ] 扩充 `guardrail.py` 中的高中超纲禁忌词库与正向初中考标词库
- [ ] 重启并完善飞书工作台 Web App 网页端与免登流程


---

## 七、 代码仓库与 GitHub 协作配置

### 1. 远程仓库信息
* **GitHub 仓库地址**：`https://github.com/dilon007/feishu_study_plam.git`
* **默认跟踪分支**：`main`
* **远程仓库别名**：`origin`

### 2. GitHub 鉴权凭证 (PAT Token)
* **Token**：`github_pat_11AAS2QBQ0T3M4sQb6Idsx_***************************************************`（已持久化在本地 `.git/config` 凭证库中，避免明文泄露被 GitHub 吊销）
* **Token 类型**：GitHub Fine-grained Personal Access Token
* **关键权限要求**：`Repository permissions -> Contents` 必须为 **Read and write**（否则 git push 将报 403 错误）。
* **自动化推送免密配置说明**：
  本地已配置带鉴权的 remote origin，Agent 或终端免密自动推送：
  ```bash
  git remote set-url origin https://oauth2:<YOUR_GITHUB_PAT>@github.com/dilon007/feishu_study_plam.git
  ```
  > ⚠️ **注意**：公开仓库（Public）由 GitHub Secret Scanning 保护，推送时切勿包含未脱敏的明文 Token 字符串。
