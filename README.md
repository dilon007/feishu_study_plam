# 苏九学伴 · 苏州市9年级学习助手中台 部署与运维手册

> **定位说明**：本项目是专为**苏州市初中九年级（初三）学生**设计的中考备考智能化助手中台。所有教材版本严格锚定**苏科版（数学/物理）**、**译林版（英语）**、**统编版（语文/道法/历史）**，并内置**防超纲安全审查围栏**。  
> 本手册提供从**云服务器生产部署**到**飞书开放平台配置**的全流程实战操作手顺。

---

## 目录
- [一、 部署前置条件准备](#一-部署前置条件准备)
- [二、 云服务器生产环境部署手顺](#二-云服务器生产环境部署手顺)
  - [1. 安装系统依赖与环境](#1-安装系统依赖与环境)
  - [2. 拉取代码并初始化虚拟环境](#2-拉取代码并初始化虚拟环境)
  - [3. 配置环境变量 (.env)](#3-配置环境变量-env)
  - [4. 配置 systemd 后台保活服务](#4-配置-systemd-后台保活服务)
  - [5. 配置 Nginx 反向代理与 SSL 证书 (HTTPS)](#5-配置-nginx-反向代理与-ssl-证书-https)
  - [6. 开放安全组防火墙端口](#6-开放安全组防火墙端口)
- [三、 飞书开放平台详细配置手顺](#三-飞书开放平台详细配置手顺)
  - [1. 创建企业自建应用](#1-创建企业自建应用)
  - [2. 开启并配置「网页应用」能力（工作台内嵌）](#2-开启并配置网页应用能力工作台内嵌)
  - [3. 开启并配置「机器人」能力（IM 对话答疑）](#3-开启并配置机器人能力im-对话答疑)
  - [4. 配置「权限管理」清单](#4-配置权限管理清单)
  - [5. 配置「事件订阅」与消息回调](#5-配置事件订阅与消息回调)
  - [6. 预览并配置「飞书欢迎消息卡片」](#6-预览并配置飞书欢迎消息卡片)
  - [7. 发布版本与上线测试](#7-发布版本与上线测试)
- [四、 全链路验证与常见问题排查 (Troubleshooting)](#四-全链路验证与常见问题排查-troubleshooting)

---

## 一、 部署前置条件准备

在开始部署前，请确保已备齐以下资源：
1. **云服务器**：一台公网 Linux 服务器（推荐系统：Ubuntu 20.04/22.04 LTS 或 CentOS 7/8/9），具有固定的公网 IP。
2. **域名与解析**：一个二级域名（如 `study.yourdomain.com`），并将 A 记录解析至该云服务器公网 IP。
3. **SSL 证书（必须）**：飞书客户端限制所有网页应用、卡片回调 URL 必须为 **合法的 HTTPS 地址**（可通过免费的 Let's Encrypt / Certbot 申请）。
4. **飞书企业管理员/开发者账号**：可在 [飞书开放平台 (open.feishu.cn)](https://open.feishu.cn/) 创建和发布应用。

---

## 二、 云服务器生产环境部署手顺

以下步骤以 **Ubuntu 22.04 LTS** 系统为例（CentOS 系统命令见对应提示）。

### 1. 安装系统依赖与环境
连接服务器终端，执行更新与必要软件安装：
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git python3 python3-pip python3-venv nginx certbot python3-certbot-nginx
```
*(若为 CentOS: `sudo yum install -y git python3 python3-pip nginx certbot python3-certbot-nginx`)*

---

### 2. 拉取代码并初始化虚拟环境
将代码拉取至服务器的标准部署目录（如 `/data/www` 或 `/home/ubuntu`）：

```bash
# 创建并进入项目目录
sudo mkdir -p /data/www
cd /data/www

# 克隆代码仓库
git clone https://github.com/dilon007/feishu_study_plam.git
cd feishu_study_plam

# 创建并激活 Python 独立虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装后端依赖
pip install --upgrade pip
pip install -r backend/requirements.txt
```

---

### 3. 配置环境变量 (.env)
在项目根目录下创建生产环境变量文件：
```bash
nano .env
```
写入如下内容并按实际信息替换：
```ini
# 服务运行端口与主机
HOST=127.0.0.1
PORT=8000

# 飞书开放平台应用凭证 (在飞书开放平台后台获取)
FEISHU_APP_ID=cli_xxxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
FEISHU_ENCRYPT_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
FEISHU_VERIFICATION_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 业务防超纲模式 (Strict / Warning)
GUARDRAIL_MODE=strict
```
按 `Ctrl+O` 保存并按 `Ctrl+X` 退出。

---

### 4. 配置 systemd 后台保活服务
使用 systemd 管理 FastAPI 服务，实现**后台常驻、开机自启、崩溃自动重启**。

创建服务配置文件：
```bash
sudo nano /etc/systemd/system/suzhou-study.service
```

填入以下配置内容：
```ini
[Unit]
Description=Suzhou Grade 9 Feishu Study Assistant Middle Platform
After=network.target

[Service]
User=root
WorkingDirectory=/data/www/feishu_study_plam
Environment="PATH=/data/www/feishu_study_plam/venv/bin"
ExecStart=/data/www/feishu_study_plam/venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 2

Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

启动并设置开机自启：
```bash
sudo systemctl daemon-reload
sudo systemctl start suzhou-study
sudo systemctl enable suzhou-study

# 检查服务状态（显示 active (running) 即代表成功运行）
sudo systemctl status suzhou-study
```

---

### 5. 配置 Nginx 反向代理与 SSL 证书 (HTTPS)

#### ① 配置 Nginx 站点
创建 Nginx 虚拟主机配置文件：
```bash
sudo nano /etc/nginx/sites-available/suzhou-study.conf
```
写入如下反向代理配置（将 `study.yourdomain.com` 替换为你的真实域名）：
```nginx
server {
    listen 80;
    server_name study.yourdomain.com;

    # 飞书健康检查及主应用反向代理
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 支持 WebSocket（如需长连接流式输出）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

启用该配置并测试：
```bash
sudo ln -s /etc/nginx/sites-available/suzhou-study.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### ② 自动申请并安装免费 SSL 证书 (Certbot)
运行以下命令，Certbot 会自动配置 HTTPS 证书并修改 Nginx 配置：
```bash
sudo certbot --nginx -d study.yourdomain.com
```
申请完成后，在浏览器中访问 `https://study.yourdomain.com/welcome`，若能正常打开具有倒计时与苏州学科专区的欢迎页，说明服务器端部署全部成功！

---

### 6. 开放安全组防火墙端口
确保云服务商控制台（阿里云/腾讯云/华为云/AWS）的**安全组规则**已放行以下端口：
* **80** (HTTP - 用于证书续期与 301 重定向)
* **443** (HTTPS - 飞书通信必须)

---

## 三、 飞书开放平台详细配置手顺

### 1. 创建企业自建应用
1. 使用浏览器登录 [飞书开放平台开发者后台](https://open.feishu.cn/app)；
2. 点击右上角 **「创建企业自建应用」**；
3. 填写应用信息：
   * **应用名称**：`苏九学伴`（或自定义名称）
   * **应用描述**：`苏州市九年级中考备考专属学习助手中台（苏科版/译林版精准对齐）`
   * **应用图标**：上传初三中考/书本风格图标；
4. 创建成功后，在 **「凭证与基础信息」** 页面获取并记录：
   * **App ID**（形如 `cli_a1b2c3d4e5`）
   * **App Secret**

---

### 2. 开启并配置「网页应用」能力（工作台内嵌）
此功能让学生在飞书 PC 端工作台或移动端可以直接点击打开学习看板：
1. 在左侧菜单点击 **「添加应用能力」➔ 选择「网页应用」并添加**；
2. 进入「网页应用」配置页：
   * **桌面端主页 URL**：`https://study.yourdomain.com/welcome`
   * **移动端主页 URL**：`https://study.yourdomain.com/welcome`
3. 点击页面右上角保存。

---

### 3. 开启并配置「机器人」能力（IM 对话答疑）
1. 在左侧菜单点击 **「添加应用能力」➔ 选择「机器人」并添加**；
2. 机器人开启后，学生可在飞书搜索栏直接搜到“苏九学伴”，发起单聊、发送题目提问、接收每日考点卡片。

---

### 4. 配置「权限管理」清单
在左侧菜单点击 **「开发配置」➔「权限管理」**，开通以下必要权限：
* `contact:user.employee_id:readonly`（获取用户 user_id）
* `im:message`（获取与发送单聊/群聊消息）
* `im:message.p2p_msg:readonly`（接收用户发给机器人的单聊消息）
* `im:resource`（上传与下载消息中的图片，用于题目搜题）

---

### 5. 配置「事件订阅」与消息回调
用于云服务器后端接收学生在飞书发来的消息与按钮点击：
1. 在左侧菜单点击 **「开发配置」➔「事件与回调」**；
2. **Encrypt Key 与 Verification Token**：点击生成并将其更新到服务器 `.env` 文件中；
3. **请求网址 URL (Request URL)**：填入：
   ```text
   https://study.yourdomain.com/api/feishu/event
   ```
4. 点击保存，飞书会向该 URL 发送验证挑战（Challenge），后端接口返回对应字段后即验证成功；
5. 在「添加事件」中勾选订阅：
   * `接收消息 (im.message.receive_v1)`
   * `卡片回传交互 (card.action.trigger)`

---

### 6. 预览并配置「飞书欢迎消息卡片」
1. 打开官方工具：[飞书卡片搭建工具 (Card Builder)](https://open.feishu.cn/tool/cardbuilder)；
2. 点击右上角「导入 JSON」，复制本项目中 [feishu_cards/welcome_card.json](feishu_cards/welcome_card.json) 的内容并粘贴；
3. 将卡片中的跳转链接替换为你的真实线上域名 `https://study.yourdomain.com/welcome`；
4. 可以在卡片搭建工具中直接向你自己的飞书账号发送测试卡片，查看精美的移动端/桌面端卡片效果。

---

### 7. 发布版本与上线测试
1. 在左侧菜单点击 **「应用发布」➔「版本管理与发布」**；
2. 点击 **「创建版本」**：
   * 填写版本号（如 `1.0.0`）；
   * 填写更新说明（如 `首版上线：苏州市9年级专属学习中台，支持考点检索与防超纲问答`）；
   * 可用范围选择：指定测试人员或全员可用；
3. 点击提交审核（管理员账号可直接免审即时生效上线）。

---

## 四、 全链路验证与常见问题排查 (Troubleshooting)

### 1. 验证清单
| 测试项 | 预期表现 | 检查方式 |
| :--- | :--- | :--- |
| **工作台网页** | 打开飞书工作台点击应用，正常显示苏州中考倒计时与学科分类 | 飞书客户端内点击打开 |
| **防超纲安全审查** | 提问高中知识（如“空间向量求二面角”）被友好拦截并提示考纲边界 | 在输入框输入超纲问题测试 |
| **后台服务保活** | 重启服务器后服务自动拉起，无需人工手动启动 | `sudo reboot` 后验证 `systemctl status suzhou-study` |

---

### 2. 常见问题与排查命令

#### Q1: 飞书事件订阅 URL 校验失败？
* **原因**：Nginx 没有正确转发或者 SSL 证书不受信任。
* **排查**：在本地电脑运行 `curl -I https://study.yourdomain.com/welcome`，检查 HTTP 状态码是否为 200；检查服务器后台日志 `sudo journalctl -u suzhou-study -n 50`。

#### Q2: 如何查看后端实时运行日志与报错？
* **查看 FastAPI 服务日志**：
  ```bash
  sudo journalctl -u suzhou-study -f
  ```
* **查看 Nginx 访问与错误日志**：
  ```bash
  sudo tail -f /var/log/nginx/access.log
  sudo tail -f /var/log/nginx/error.log
  ```

#### Q3: 如何更新云服务器上的代码？
当我们在本地将新代码推送到 GitHub 后，只需在云服务器执行：
```bash
cd /data/www/feishu_study_plam
git pull origin main
sudo systemctl restart suzhou-study
```
即可无缝完成热更新！