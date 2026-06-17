# 储能并网检测知识问答及智能体应用系统

基于大语言模型（扣子Coze平台）的储能并网检测知识问答平台，包含 **PC用户端** 和 **PC管理端**。

---

## 📋 目录

- [项目简介](#项目简介)
- [主要功能](#主要功能)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [安装部署](#安装部署)
- [配置说明](#配置说明)
- [默认账号](#默认账号)
- [API接口](#api接口)

---

## 项目简介

本系统以AI技术为手段，集成 **扣子(Coze)开放平台**，通过整合专业文档与实时数据，构建一个智能、准确、高效的储能并网技术知识交互平台，辅助专业人员进行技术查询与决策支持。

## 主要功能

### 用户端功能
| 功能 | 说明 |
|------|------|
| 知识问答 | 基于Coze大模型的专业知识智能问答（流式输出） |
| 智能创作 | AI自动生成技术方案、检测报告等专业文档 |
| 智能体 | 创建专属AI助手，自定义人设与开场白（同步至Coze平台） |
| 知识库 | 用户自建知识库，上传文本/网页至Coze平台管理 |
| 对话历史 | 查看和管理历史对话记录 |
| 常见问题 | 浏览储能并网相关FAQ |

### 管理端功能
| 功能 | 说明 |
|------|------|
| 数据统计 | 系统整体数据统计和可视化 |
| 用户管理 | 用户信息管理、状态控制 |
| FAQ管理 | 常见问题的增删改查 |
| 对话记录 | 查看所有用户对话记录 |
| 扣子平台 | 配置Coze Token/Bot/知识库，管理工作空间和会话 |

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.8+ / Flask / PyMySQL / requests |
| 前端 | HTML5 / Tailwind CSS / Font Awesome / JavaScript |
| 数据库 | MySQL 5.7+ |
| AI平台 | 扣子(Coze) 开放平台 API |

---

## 项目结构

```
GTK26010501/
├── python_scripts/
│   ├── app.py                   # Flask后端 (所有API)
│   └── requirements.txt         # Python依赖
├── database_scripts/
│   ├── database.sql             # 数据库建表脚本 (首次部署执行)
│   ├── test_data.sql            # 测试数据 (可选)
│   └── coze_migration.sql       # 扣子字段迁移脚本
├── start.bat                    # Windows一键启动脚本
│
├── templates/                   # 前端页面
│   ├── ── 用户端页面 ──
│   ├── index.html               # 首页
│   ├── login.html               # 登录
│   ├── register.html            # 注册
│   ├── chat.html                # 知识问答 / 智能体对话
│   ├── create.html              # 智能创作
│   ├── agent.html               # 智能体管理
│   ├── knowledge.html           # 用户知识库管理
│   ├── history.html             # 历史记录
│   ├── faq.html                 # 常见问题
│   │
│   ├── ── 管理端页面 ──
│   ├── admin-login.html         # 管理员登录
│   ├── admin-dashboard.html     # 数据统计
│   ├── admin-users.html         # 用户管理
│   ├── admin-faq.html           # FAQ管理
│   ├── admin-conversations.html # 对话记录
│   ├── admin-coze.html          # 扣子平台配置
│   └── admin-knowledge.html     # 知识库管理 (已隐藏)
```

---

## 安装部署

### 前置要求

- **Python** 3.8 及以上
- **MySQL** 5.7 及以上
- **扣子(Coze)账号** — 在 [coze.cn](https://www.coze.cn) 注册

### 第一步：安装 Python 依赖

```bash
pip install -r python_scripts/requirements.txt
```

依赖列表：
- Flask==2.3.3
- Flask-CORS==4.0.0
- PyMySQL==1.1.0
- requests==2.31.0

### 第二步：初始化数据库

1. 登录 MySQL，执行建表脚本：

```bash
mysql -u root -p < database_scripts/database.sql
```

2. 执行数据库迁移脚本：

```bash
mysql -u root -p < database_scripts/coze_migration.sql
```

3.（可选）导入测试数据：

```bash
mysql -u root -p < database_scripts/test_data.sql
```

### 第三步：修改数据库连接

打开 `python_scripts/app.py`，找到 **DB_CONFIG**（约第60行左右），修改为你的数据库信息：

```python
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '你的MySQL密码',    # ← 改这里
    'database': 'energy_storage_qa',
    'charset': 'utf8mb4'
}
```

### 第四步：启动服务

在根目录下执行：
```bash
python python_scripts/app.py
```

或 Windows 双击 `start.bat` 即可启动。

服务启动后访问：**http://localhost:5000**

### 第五步：配置扣子(Coze)平台

> ⚠️ **必须完成此步骤**，否则AI问答、智能体等功能无法使用。

1. 登录管理后台：http://localhost:5000/admin-login.html
2. 进入「扣子平台」页面
3. 填写以下配置项：

| 配置项 | 获取方式 | 是否必填 |
|--------|----------|----------|
| **API访问令牌(PAT)** | [扣子开放平台](https://www.coze.cn/open/oauth/pats) → 创建令牌 | ✅ 必填 |
| **默认工作空间ID** | 工作空间URL中 `space/` 后的数字 | ✅ 必填 |
| **默认对话Bot ID** | 在Coze平台创建Bot后获取Bot ID | ✅ 必填 |
| 智能创作Bot ID | 单独用于创作功能的Bot ID | 选填 |
| 默认知识库ID | 在Coze平台知识库页面URL中获取 | 选填 |

4. 点击「保存配置」
5. 点击「测试连接」验证是否连通

---

## 配置说明

### 数据库配置
修改 `app.py` 中的 `DB_CONFIG` 字典。

### 扣子(Coze)配置
所有扣子相关配置存储在数据库 `system_config` 表中，可通过管理后台「扣子平台」页面可视化管理：

```
coze_api_token          → API访问令牌
coze_default_space_id   → 工作空间ID
coze_default_bot_id     → 默认对话Bot ID
coze_creation_bot_id    → 智能创作Bot ID
coze_default_dataset_id → 默认知识库ID
```

更换扣子账号时，只需在管理后台修改这些配置，**无需修改代码或重启服务**。

---

## 默认账号

### 用户端
- 访问地址：http://localhost:5000/index.html
- 测试账号：`张三` / `123456`

### 管理端
- 访问地址：http://localhost:5000/admin-login.html
- 测试账号：`admin` / `admin123`

> 💡 以上账号需先导入 `test_data.sql` 测试数据才可使用。

---

## 数据库设计

> 完整建表语句见 `database.sql`

| 序号 | 表名 | 说明 |
|------|------|------|
| 1 | users | 用户表 |
| 2 | admins | 管理员表 |
| 3 | knowledge_documents | 知识库文档表（管理员管理） |
| 4 | conversations | 对话会话表 |
| 5 | messages | 对话消息表 |
| 6 | agents | 智能体表（关联Coze Bot） |
| 7 | faqs | 常见问题表 |
| 8 | creations | 创作作品表 |
| 9 | system_config | 系统配置表（含Coze配置） |
| 10 | user_datasets | 用户知识库表（关联Coze Dataset） |

---

## API接口

### 用户认证
```
POST /api/register              用户注册
POST /api/login                 用户登录
POST /api/admin/login           管理员登录
POST /api/logout                退出登录
```

### 知识问答 (流式)
```
POST /api/conversations/create          创建对话
GET  /api/conversations/list            对话列表
GET  /api/conversations/<id>/messages   获取消息
POST /api/conversations/<id>/send_stream 发送消息(SSE流式)
DELETE /api/conversations/delete/<id>   删除对话
```

### 智能体
```
GET  /api/agents/list            智能体列表
POST /api/agents/create          创建智能体 (同步至Coze)
PUT  /api/agents/update/<id>     更新智能体
DELETE /api/agents/delete/<id>   删除智能体
```

### 智能创作
```
GET  /api/creations/list         创作列表
POST /api/creations/create       创建作品 (AI生成)
```

### 用户知识库
```
POST /api/user/datasets/create                     创建知识库
GET  /api/user/datasets/list                       知识库列表
DELETE /api/user/datasets/delete/<id>              删除知识库
POST /api/user/datasets/<id>/files/create          创建知识文件
GET  /api/user/datasets/<id>/files/list            文件列表
POST /api/user/datasets/<id>/files/delete          删除文件
```

### FAQ
```
GET  /api/faq/list               FAQ列表
POST /api/faq/view/<id>          记录查看
POST /api/admin/faq/add          添加FAQ（管理员）
PUT  /api/admin/faq/update/<id>  更新FAQ（管理员）
DELETE /api/admin/faq/delete/<id> 删除FAQ（管理员）
```

### 管理员
```
GET  /api/admin/users/list               用户列表
PUT  /api/admin/users/toggle-status/<id> 切换用户状态
GET  /api/admin/conversations/list       对话记录
GET  /api/admin/statistics               统计数据
```

### 扣子平台管理（管理员）
```
GET  /api/coze/config            获取配置
POST /api/coze/config            保存配置
GET  /api/coze/test              测试连接
GET  /api/coze/workspaces        工作空间列表
GET  /api/coze/bots              智能体列表
GET  /api/coze/datasets          知识库列表
POST /api/coze/datasets/create   创建知识库
DELETE /api/coze/datasets/delete/<id> 删除知识库
```

---

## 常见问题

**Q: 启动后 AI 问答没有响应？**
A: 请确认已在管理后台配置了 Coze API Token 和 Bot ID，并点击「测试连接」验证。

**Q: 如何更换扣子账号？**
A: 登录管理后台 → 扣子平台 → 修改 API 访问令牌和工作空间ID → 保存配置。无需重启服务。

**Q: 知识库文件创建失败？**
A: 检查 Coze API Token 是否有 `createDocument` 权限，以及知识库和文件类型是否匹配（文本型只能上传文本/网页）。

---

## 许可证

MIT License
