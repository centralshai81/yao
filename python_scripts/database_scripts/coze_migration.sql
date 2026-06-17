-- 扣子(Coze)平台集成 - 数据库更新脚本

DELIMITER $$
DROP PROCEDURE IF EXISTS `AddCozeMigrationColumns`$$
CREATE PROCEDURE `AddCozeMigrationColumns`()
BEGIN
    -- 在agents表中添加coze_bot_id字段
    IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'agents' AND COLUMN_NAME = 'coze_bot_id') THEN
        ALTER TABLE agents ADD COLUMN coze_bot_id VARCHAR(100) DEFAULT NULL COMMENT '扣子平台Bot ID';
    END IF;

    -- 在knowledge_documents表中添加coze同步状态字段
    IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'knowledge_documents' AND COLUMN_NAME = 'coze_synced') THEN
        ALTER TABLE knowledge_documents ADD COLUMN coze_synced TINYINT DEFAULT 0 COMMENT '是否已同步到扣子: 0-未同步, 1-已同步';
    END IF;

    IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'knowledge_documents' AND COLUMN_NAME = 'coze_dataset_id') THEN
        ALTER TABLE knowledge_documents ADD COLUMN coze_dataset_id VARCHAR(100) DEFAULT NULL COMMENT '扣子知识库ID';
    END IF;
END$$
DELIMITER ;

CALL AddCozeMigrationColumns();
DROP PROCEDURE AddCozeMigrationColumns;

-- 添加扣子配置到系统配置表
INSERT INTO system_config (config_key, config_value, description) VALUES 
('coze_default_bot_id', '', '扣子默认对话Bot ID'),
('coze_creation_bot_id', '', '扣子智能创作Bot ID'),
('coze_api_token', 'pat_y2eb1WyhDZi57vSGeKKdHITn4P3V8x13IvPOWaIXQImG0JzPedgq2FRCBui44Ezg', '扣子API访问令牌'),
('coze_default_space_id', '', '扣子默认工作空间ID'),
('coze_default_dataset_id', '', '扣子默认知识库ID')
ON DUPLICATE KEY UPDATE config_value = VALUES(config_value);
