# 演示数据与快速上手

本文档帮你在一台全新机器上把系统跑起来，并写入一套可直接体验的中文演示数据。

## 1. 写入演示数据

后端提供幂等的 `seed-demo` 命令（重复执行不会产生重复数据）：

```powershell
cd D:\saas\backend

# 首次写入（自动建表 + 灌入演示数据）
.\.venv\Scripts\python.exe -m app.cli seed-demo

# 想清空重来（会删除所有表再重建）
.\.venv\Scripts\python.exe -m app.cli seed-demo --reset
```

也可以让服务启动时自动写入：在 `backend/.env` 或系统环境变量里设置

```
SEED_DEMO=true
```

设置后每次启动（`APP_ENV` 为 `development` / `test`）都会自动补齐演示数据，缺什么补什么。

## 2. 演示账号（登录用）

写入演示数据后可用以下账号登录。**所有演示用户的登录密码都在这里：**

| 角色 | 邮箱 | 密码 | 说明 |
| --- | --- | --- | --- |
| 超级管理员 | `admin@example.com` | `Admin123456!` | owner 角色，拥有全部权限 |
| 产品经理 | `pm@example.com` | `Demo123456!` | member 角色 |
| 前端工程师 | `dev1@example.com` | `Demo123456!` | member 角色 |
| 后端工程师 | `dev2@example.com` | `Demo123456!` | member 角色 |
| 访客 | `guest@example.com` | `Demo123456!` | guest 角色，只读 |

> 开启 `SEED_DEMO=true` 后，登录页会自动出现「演示账号」按钮，点一下即可自动填入，不用手打。

## 3. 启动系统

### 后端（FastAPI）

```powershell
cd D:\saas\backend
$env:APP_ENV = "development"
$env:SEED_DEMO = "true"          # 可选：自动写演示数据
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

- 健康检查： <http://127.0.0.1:8000/healthz>
- 接口文档（Swagger）： <http://127.0.0.1:8000/docs>

默认使用 SQLite，无需安装数据库。

### 前端（React + Vite）

```powershell
cd D:\saas\frontend
npm install
npm run dev
```

打开 <http://localhost:5173>，用上面的账号登录即可。

> 前端开发服务器已把 `/api` 代理到后端，确保后端跑在 8000 端口即可。

## 4. 数据库怎么访问

### 方式 A：本地开发（默认 SQLite）

后端默认连接 `backend/saas.db`（SQLite 文件），零配置：

- 文件位置：`D:\saas\backend\saas.db`
- 图形化查看：用 [DB Browser for SQLite](https://sqlitebrowser.org/) 或 DBeaver 打开该文件。
- 命令行查看：

```powershell
cd D:\saas\backend
.\.venv\Scripts\python.exe -c "import sqlite3;c=sqlite3.connect('saas.db');print(c.execute('select email,is_superuser from users').fetchall())"
```

- 连接串：`sqlite+aiosqlite:///./saas.db`

### 方式 B：Docker Compose（MySQL 8 + Redis）

`docker-compose.yml` 里已经配好 MySQL，容器启动后按下面信息连接：

| 项 | 值 |
| --- | --- |
| 主机 | `127.0.0.1` |
| 端口 | `3306` |
| 数据库 | `saas` |
| 用户名 | `saas` |
| 密码 | `saas` |
| 连接串 | `mysql+asyncmy://saas:saas@127.0.0.1:3306/saas?charset=utf8mb4` |

用 Navicat / DBeaver / DataGrip 按上表连接；或在命令行：

```bash
docker compose exec mysql mysql -usaas -psaas saas
docker compose exec mysql mysql -usaas -psaas saas -e "select id,email from users;"
```

> 生产环境请务必修改默认密码：改 `docker-compose.yml` / `.env` 里的 `DATABASE_URL` 与 MySQL 账号。

## 5. 演示数据包含什么

写入后会得到一套可直接体验各功能的数据：

- **用户 / 权限**：5 个用户，覆盖 owner / member / guest 角色；内置 13 项权限。
- **团队**：产品研发团队、设计团队。
- **项目**：`AICRM 客户管理系统`、`官网改版`。
- **看板**：每个项目一个看板，含「待办 / 进行中 / 待评审 / 已完成」等列。
- **任务**：9 条任务，含优先级、指派、截止日期、父子任务（子任务）、评论。
- **标签**：缺陷 / 新功能 / 紧急 / 文档 / 优化。
- **文档**：2 篇带版本历史的文档。
- **通知**：未读通知若干，可测试通知中心与偏好设置。
- **订阅计费**：免费 / 专业 / 旗舰 3 个套餐，1 个生效订阅，2 笔订单（已支付 + 待支付）。
- **集成**：企业微信 / 邮件 / 支付宝 / 微信支付占位配置。
- **系统设置**：站点名称、语言、密码策略等。

## 6. 登录后能做什么

左侧导航按权限显示，管理员登录后可见全部功能：

- **工作台**：项目数、任务数、未读通知、用户数、团队数统计。
- **项目**：新建 / 归档 / 删除；进入后是看板，可拖动任务、编辑任务详情、写评论、加标签、建子任务。
- **团队**：新建团队、增减成员。
- **文档**：富文本编辑，自动保留版本历史。
- **通知**：查看、已读、全部已读；通知偏好（站内 / 邮件 / 企业微信）。
- **计费**：套餐、订阅、订单、发起支付（需配置支付密钥才会真实下单）。
- **设置**：修改密码、开启 TOTP 双因素、许可（License）激活。
- **用户管理 / 审计日志**：仅管理员可见。

## 7. 常见问题

- **登录返回 401 / 密码错误**：确认执行过 `seed-demo`，且邮箱密码与上表完全一致（区分大小写）。
- **终端中文显示乱码**：只是 Windows 控制台编码问题，数据库里的中文是正常的，在网页里显示正常。
- **想重置所有数据**：执行 `seed-demo --reset`，或直接删除 `backend/saas.db` 后重启。
