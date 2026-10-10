import { ACCESS_TOKEN, PHONE } from '@/constants/home.constants';
import BasicLayout from '@/pages/Login/BasicLayout';
import LoginLangSwitcher from '@/pages/Login/LoginLangSwitcher';
import { apiLogout } from '@/services/account';
import { dict } from '@/services/i18nRuntime';
import {
  getMyEnterprises,
  selectEnterprise,
  type Membership,
} from '@/services/tenantMembership';
import {
  getOnboarding,
  type OrganizationProfile,
} from '@/services/tenantOnboarding';
import { applyTenantSession } from '@/services/tenantSession';
import { maskAccount } from '@/utils/tenantLogin';
import { SearchOutlined } from '@ant-design/icons';
import {
  Alert,
  Button,
  Empty,
  Input,
  Radio,
  Space,
  Spin,
  Tag,
  Typography,
  message,
} from 'antd';
import classNames from 'classnames';
import React, { useEffect, useRef, useState } from 'react';
import { history } from 'umi';
import styles from './index.less';
import Onboarding from './Onboarding';

const cx = classNames.bind(styles);
const { Title, Text } = Typography;

/**
 * 角色标签的文案。
 *
 * 不用 map 存 key 再拼字符串：i18n 的合法性检查（scripts/check-hardcoded-i18n.js）
 * 需要看到字面量 key，拼接出来的 key 既躲过了静态检查，写错了也只能等运行时
 * 打出 [i18n] Missing translation entry。这里逐条写全，检查才能覆盖到。
 *
 * 另外，服务端返回的 'OWNER' 不能直接当 key 末段使用：末段必须以小写字母开头
 * （I18N_KEY_REGEX），否则 dict() 校验不通过、原样返回 key 字符串，
 * 界面上就会显示出 "PC.Pages.TenantSelect.OWNER" 这种东西。
 */
const roleLabel = (role: string): string => {
  // 遇到前端还不认识的角色时回退原始值，而不是显示空标签
  switch (role) {
    case 'OWNER':
      return dict('PC.Pages.TenantSelect.roleOwner');
    case 'ADMIN':
      return dict('PC.Pages.TenantSelect.roleAdmin');
    case 'MEMBER':
      return dict('PC.Pages.TenantSelect.roleMember');
    default:
      return role;
  }
};

type SelectState = 'loading' | 'ready' | 'error';

/**
 * 登录第二步：选择企业。
 *
 * 身份已验证但尚未选择企业时，登录接口返回 stage=TENANT_SELECTION_REQUIRED，
 * 令牌只写在 HttpOnly Cookie 中，此页面无权访问任何业务接口。
 * 选择成功后由 applyTenantSession 清理缓存、写入企业令牌并整页跳转到工作台。
 */
const TenantSelect: React.FC = () => {
  const [rows, setRows] = useState<Membership[]>([]);
  const [state, setState] = useState<SelectState>('loading');
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [query, setQuery] = useState('');
  const visibleRows = rows.filter((row) =>
    `${row.name} ${row.tenantId}`
      .toLocaleLowerCase()
      .includes(query.trim().toLocaleLowerCase()),
  );
  const [onboarding, setOnboarding] = useState<{
    enabled: boolean;
    profile: OrganizationProfile | null;
  }>({ enabled: false, profile: null });
  const [account] = useState(() => localStorage.getItem(PHONE) || '');
  const loadVersion = useRef(0);

  const load = async () => {
    // 本页只属于身份阶段：多企业登录响应不回 token，本地不应存在企业令牌。
    // 手里已经有企业令牌还进到这里，说明是手输地址，直接回工作台。
    //
    // 这里不能改用平台能力接口来判断多企业开关：/api/platform/capabilities
    // 需要企业会话，身份票据调用只会拿到 401，反而把用户踢回登录页。
    if (localStorage.getItem(ACCESS_TOKEN)) {
      history.replace('/home');
      return;
    }

    setState('loading');
    const version = ++loadVersion.current;
    try {
      const list = await getMyEnterprises();
      const profile = await getOnboarding();
      if (version !== loadVersion.current) return;
      setOnboarding(profile);
      // 已撤销的成员关系不能进入，服务端在 select 时也会再校验一次
      const active = (list || []).filter((row) => row.status === 'ACTIVE');
      setRows(active);
      // 只有一家企业时预选，但仍要求用户点击进入，不自动跳转
      setSelectedId(active.length === 1 ? active[0].tenantId : null);
      setState('ready');
    } catch {
      if (version !== loadVersion.current) return;
      // 身份票据 300 秒过期时，全局 4010 处理器已经会跳回登录页；
      // 这里保留可重试的错误态，避免用户停在无反馈的白屏上。
      setState('error');
    }
  };

  useEffect(() => {
    void load();
    return () => { loadVersion.current += 1; };
  }, []);

  const enter = async () => {
    if (
      selectedId === null ||
      submitting ||
      (onboarding.enabled && !onboarding.profile)
    ) {
      return;
    }
    setSubmitting(true);
    try {
      const session = await selectEnterprise(selectedId);
      applyTenantSession(session);
    } catch {
      message.error(dict('PC.Pages.TenantSelect.selectFailed'));
      setSubmitting(false);
      // 失败可能是成员刚被撤销或企业被停用，重新拉取列表
      void load();
    }
  };

  const switchAccount = async () => {
    try {
      await apiLogout();
    } catch {
      // 注销失败也要回登录页，否则用户会卡在选择页
    }
    localStorage.removeItem(PHONE);
    history.replace('/login');
  };

  const renderBody = () => {
    if (state === 'loading') {
      return (
        <div className={cx(styles.center)}>
          <Spin />
          <Text type="secondary">{dict('PC.Pages.TenantSelect.loading')}</Text>
        </div>
      );
    }

    if (state === 'error') {
      return (
        <Space direction="vertical" size={16} style={{ width: '100%' }}>
          <Alert
            type="error"
            showIcon
            message={dict('PC.Pages.TenantSelect.loadFailed')}
          />
          <Space>
            <Button onClick={load}>
              {dict('PC.Pages.TenantSelect.retry')}
            </Button>
            <Button type="link" onClick={() => history.replace('/login')}>
              {dict('PC.Pages.TenantSelect.backToLogin')}
            </Button>
          </Space>
        </Space>
      );
    }

    if (rows.length === 0) {
      return (
        <div className={cx(styles.center)}>
          <Empty description={dict('PC.Pages.TenantSelect.noEnterprise')} />
          <Text type="secondary">
            {dict('PC.Pages.TenantSelect.noEnterpriseHint')}
          </Text>
          <Button onClick={switchAccount}>
            {dict('PC.Pages.TenantSelect.switchAccount')}
          </Button>
        </div>
      );
    }

    return (
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <Input
          allowClear
          prefix={<SearchOutlined />}
          value={query}
          disabled={submitting}
          placeholder={dict('PC.Pages.TenantSelect.searchEnterprise')}
          aria-label={dict('PC.Pages.TenantSelect.searchEnterprise')}
          onChange={(event) => {
            setQuery(event.target.value);
            setSelectedId(null);
          }}
        />
        {visibleRows.length === 0 && (
          <Empty description={dict('PC.Pages.TenantSelect.noSearchResults')} />
        )}
        <Radio.Group
          className={cx(styles.list)}
          value={selectedId}
          onChange={(event) => setSelectedId(event.target.value)}
        >
          {visibleRows.map((row) => (
            <Radio
              key={row.tenantId}
              value={row.tenantId}
              disabled={submitting}
              className={cx(
                styles.item,
                selectedId === row.tenantId && styles.selected,
              )}
            >
              <span className={cx(styles.name)}>
                {row.name}
                <small className={styles.tenantId}>ID {row.tenantId}</small>
              </span>
              <Tag>{roleLabel(row.role)}</Tag>
            </Radio>
          ))}
        </Radio.Group>
        <Button
          type="primary"
          block
          size="large"
          loading={submitting}
          disabled={
            selectedId === null || (onboarding.enabled && !onboarding.profile)
          }
          onClick={enter}
        >
          {dict('PC.Pages.TenantSelect.enter')}
        </Button>
      </Space>
    );
  };

  return (
    <>
      <LoginLangSwitcher />
      <BasicLayout>
        <div className={cx(styles.panel)}>
          <Title level={3}>{dict('PC.Pages.TenantSelect.title')}</Title>
          <div className={cx(styles.account)}>
            <Text type="secondary">
              {dict('PC.Pages.TenantSelect.account')}
              {account
                ? maskAccount(account)
                : dict('PC.Pages.TenantSelect.accountUnknown')}
            </Text>
            <Button type="link" size="small" disabled={submitting} onClick={switchAccount}>
              {dict('PC.Pages.TenantSelect.switchAccount')}
            </Button>
          </div>
          {state === 'ready' && onboarding.enabled && (
            <Onboarding
              profile={onboarding.profile}
              onSaved={() => void load()}
            />
          )}
          {renderBody()}
        </div>
      </BasicLayout>
    </>
  );
};

export default TenantSelect;
