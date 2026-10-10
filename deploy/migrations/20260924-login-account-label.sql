-- Run after backend language initialization. Existing translations are preserved.
INSERT IGNORE INTO i18n_config
    (_tenant_id, type, side, module, data_id, lang, field_key, field_value)
SELECT _tenant_id, type, side, module, data_id, lang,
       'PC.Pages.Login.inputAccountPlaceholder',
       CASE LOWER(lang)
           WHEN 'zh-cn' THEN '请输入用户名、邮箱或手机号'
           WHEN 'zh-tw' THEN '請輸入使用者名稱、電子郵件或手機號碼'
           WHEN 'zh-hk' THEN '請輸入用戶名稱、電郵或手機號碼'
           WHEN 'ja-jp' THEN 'ユーザー名、メールアドレス、または電話番号を入力してください'
           ELSE 'Enter your username, email or phone number'
       END
FROM i18n_config
WHERE type = 'System'
  AND side = 'PC'
  AND field_key = 'PC.Pages.Login.inputEmailPlaceholder';
