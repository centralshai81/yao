-- ============================================================
-- 储能并网检测知识问答系统 - 数据库初始化脚本
-- 版本: 2.0 (含扣子Coze平台集成)
-- 使用方式: mysql -u root -p < database.sql
-- ============================================================

-- 1. 创建数据库
CREATE DATABASE IF NOT EXISTS energy_storage_qa DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE energy_storage_qa;

-- ============================================================
-- 2. 核心业务表
-- ============================================================

-- 2.1 用户表
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
    password VARCHAR(32) NOT NULL COMMENT '密码(MD5加密)',
    email VARCHAR(100) NOT NULL UNIQUE COMMENT '邮箱',
    phone VARCHAR(20) COMMENT '手机号',
    avatar VARCHAR(255) DEFAULT 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=200' COMMENT '头像',
    status TINYINT DEFAULT 1 COMMENT '状态: 1-正常, 0-禁用',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_username (username),
    INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- 2.2 管理员表
CREATE TABLE IF NOT EXISTS admins (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE COMMENT '管理员用户名',
    password VARCHAR(32) NOT NULL COMMENT '密码(MD5加密)',
    email VARCHAR(100) NOT NULL COMMENT '邮箱',
    role VARCHAR(20) DEFAULT 'admin' COMMENT '角色',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='管理员表';

-- 2.3 知识库文档表 (管理员后台管理的知识库)
CREATE TABLE IF NOT EXISTS knowledge_documents (
    id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(200) NOT NULL COMMENT '文档标题',
    category VARCHAR(50) NOT NULL COMMENT '分类',
    content TEXT NOT NULL COMMENT '文档内容',
    file_url VARCHAR(255) COMMENT '文件URL',
    file_type VARCHAR(20) COMMENT '文件类型',
    file_size INT COMMENT '文件大小(KB)',
    tags VARCHAR(200) COMMENT '标签(逗号分隔)',
    upload_by INT COMMENT '上传者ID',
    status TINYINT DEFAULT 1 COMMENT '状态: 1-已发布, 0-草稿',
    view_count INT DEFAULT 0 COMMENT '查看次数',
    coze_synced TINYINT DEFAULT 0 COMMENT '是否已同步到扣子: 0-未同步, 1-已同步',
    coze_dataset_id VARCHAR(100) DEFAULT NULL COMMENT '扣子知识库ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_category (category),
    INDEX idx_status (status),
    FOREIGN KEY (upload_by) REFERENCES admins(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识库文档表';

-- 2.4 对话会话表
CREATE TABLE IF NOT EXISTS conversations (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL COMMENT '用户ID',
    title VARCHAR(200) DEFAULT '新对话' COMMENT '对话标题',
    type VARCHAR(20) DEFAULT 'qa' COMMENT '类型: qa-问答, create-创作, agent-智能体',
    agent_id INT COMMENT '关联的智能体ID(智能体模式)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_user_id (user_id),
    INDEX idx_type (type),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='对话会话表';

-- 2.5 对话消息表
CREATE TABLE IF NOT EXISTS messages (
    id INT PRIMARY KEY AUTO_INCREMENT,
    conversation_id INT NOT NULL COMMENT '会话ID',
    role VARCHAR(20) NOT NULL COMMENT '角色: user-用户, assistant-助手',
    content TEXT NOT NULL COMMENT '消息内容',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_conversation_id (conversation_id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='对话消息表';

-- 2.6 智能体表 (含扣子Bot关联)
CREATE TABLE IF NOT EXISTS agents (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL COMMENT '创建者ID',
    name VARCHAR(100) NOT NULL COMMENT '智能体名称',
    description TEXT COMMENT '描述',
    avatar VARCHAR(255) DEFAULT 'https://images.unsplash.com/photo-1677442136019-21780ecad995?w=200' COMMENT '头像',
    system_prompt TEXT COMMENT '系统提示词(人设与回复逻辑)',
    temperature DECIMAL(3,2) DEFAULT 0.70 COMMENT '温度参数',
    max_tokens INT DEFAULT 2000 COMMENT '最大token数',
    is_public TINYINT DEFAULT 0 COMMENT '是否公开: 1-公开, 0-私有',
    use_count INT DEFAULT 0 COMMENT '使用次数',
    coze_bot_id VARCHAR(100) DEFAULT NULL COMMENT '扣子平台Bot ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_user_id (user_id),
    INDEX idx_is_public (is_public),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='智能体表';

-- 2.7 FAQ常见问题表
CREATE TABLE IF NOT EXISTS faqs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    category VARCHAR(50) NOT NULL COMMENT '分类',
    question VARCHAR(500) NOT NULL COMMENT '问题',
    answer TEXT NOT NULL COMMENT '答案',
    order_num INT DEFAULT 0 COMMENT '排序',
    status TINYINT DEFAULT 1 COMMENT '状态: 1-显示, 0-隐藏',
    view_count INT DEFAULT 0 COMMENT '查看次数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_category (category),
    INDEX idx_status (status),
    INDEX idx_order (order_num)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='常见问题表';

-- 2.8 创作作品表
CREATE TABLE IF NOT EXISTS creations (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL COMMENT '用户ID',
    title VARCHAR(200) NOT NULL COMMENT '作品标题',
    type VARCHAR(50) NOT NULL COMMENT '类型: 技术方案, 技术报告, 检测报告等',
    prompt TEXT NOT NULL COMMENT '创作提示词',
    content TEXT NOT NULL COMMENT 'AI生成内容',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_user_id (user_id),
    INDEX idx_type (type),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='创作作品表';

-- ============================================================
-- 3. 系统配置与扣子集成表
-- ============================================================

-- 3.1 系统配置表
CREATE TABLE IF NOT EXISTS system_config (
    id INT PRIMARY KEY AUTO_INCREMENT,
    config_key VARCHAR(50) NOT NULL UNIQUE COMMENT '配置键',
    config_value TEXT COMMENT '配置值',
    description VARCHAR(200) COMMENT '描述',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统配置表';

-- 3.2 用户知识库表 (用户自建知识库 -> 同步到扣子平台)
CREATE TABLE IF NOT EXISTS user_datasets (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL COMMENT '用户ID',
    name VARCHAR(200) NOT NULL COMMENT '知识库名称',
    description TEXT COMMENT '描述',
    format_type INT DEFAULT 0 COMMENT '类型: 0-文本, 1-表格, 2-图片',
    coze_dataset_id VARCHAR(100) DEFAULT '' COMMENT '扣子平台知识库ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_user_id (user_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户知识库表';

-- ============================================================
-- 4. 初始化扣子平台配置项 (首次安装需要执行)
-- ============================================================
INSERT INTO system_config (config_key, config_value, description) VALUES
('coze_api_token',          '', '扣子API访问令牌(PAT) - 必填'),
('coze_default_space_id',   '', '扣子默认工作空间ID - 必填'),
('coze_default_bot_id',     '', '扣子默认对话Bot ID - 必填'),
('coze_creation_bot_id',    '', '扣子智能创作Bot ID - 选填'),
('coze_default_dataset_id', '', '扣子默认知识库ID - 选填'),
('site_name',               '储能并网检测知识问答平台', '网站名称'),
('site_description',        '基于大语言模型的储能并网技术知识交互平台', '网站描述'),
('max_conversation_length', '50', '单个对话最大消息数'),
('default_model_temperature','0.7', '默认模型温度参数')
ON DUPLICATE KEY UPDATE config_key = config_key;
