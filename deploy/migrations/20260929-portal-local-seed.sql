-- Local development only. Apply after 20260929-portals.sql.
-- This does not copy business resources or modify any existing credentials.
START TRANSACTION;
SET @portal_tenant = (SELECT CAST(JSON_UNQUOTE(JSON_EXTRACT(config_json, '$.tenantId')) AS UNSIGNED)
    FROM platform_portal WHERE slug='zhichuangbei');
SET @portal_created = @portal_tenant IS NULL;
INSERT INTO tenant(name,description,status,domain)
    SELECT '智创杯', 'Local competition portal', 'Enabled', 'zhichuangbei.portal.invalid' WHERE @portal_tenant IS NULL;
SET @portal_tenant = COALESCE(@portal_tenant, LAST_INSERT_ID());
INSERT INTO tenant_config(_tenant_id,description,name,value,category,input_type,data_type,notice,placeholder,min_height,required,sort)
    SELECT @portal_tenant,description,name,value,category,input_type,data_type,notice,placeholder,min_height,required,sort
    FROM tenant_config source WHERE source._tenant_id=1
    AND NOT EXISTS (SELECT 1 FROM tenant_config target WHERE target._tenant_id=@portal_tenant AND target.name=source.name);
INSERT IGNORE INTO tenant_membership(tenant_id,user_id,role,status)
    SELECT @portal_tenant,id,'OWNER','ACTIVE' FROM user WHERE id=1 AND user_name='admin' AND role='Admin';
UPDATE tenant_config SET value=CAST('0' AS JSON) WHERE _tenant_id=@portal_tenant AND name='openRegister';
UPDATE tenant_config SET value=CAST('0' AS JSON)
    WHERE @portal_created AND _tenant_id=@portal_tenant AND name IN ('defaultAgentId','defaultTaskAgentId');
UPDATE tenant_config SET value=JSON_ARRAY('com.alibaba.fastjson2.JSONArray',JSON_ARRAY())
    WHERE @portal_created AND _tenant_id=@portal_tenant AND name IN ('defaultAgentIds','recommendAgentIds','officialAgentIds');
INSERT IGNORE INTO platform_portal(slug,config_json) VALUES('zhichuangbei',JSON_OBJECT(
    'slug','zhichuangbei','tenantId',@portal_tenant,
    'title','2026华为智创杯·AI智能体开发大赛',
    'subtitle','智能体搭建与应用开发实践平台',
    'logo','/logo/logo-light.png','favicon','/logo/logo-light.png','accent','#1677ff','enabled',true));
COMMIT;
