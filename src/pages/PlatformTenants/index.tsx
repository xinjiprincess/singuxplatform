import WorkspaceLayout from '@/components/WorkspaceLayout';
import { dict } from '@/services/i18nRuntime';
import {
  getPlatformCapabilities,
  getPlatformTenants,
  updateTenantPolicy,
} from '@/services/tenantPolicy';
import {
  QUOTA_METRICS,
  type TenantPolicy,
  type TenantPolicyView,
} from '@/types/interfaces/tenantPolicy';
import { normalizeTenantPolicy } from '@/utils/tenantPolicy';
import { EditOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import {
  Alert,
  Button,
  Form,
  Input,
  InputNumber,
  Modal,
  Result,
  Select,
  Space,
  Spin,
  Table,
  message,
} from 'antd';
import { useEffect, useState } from 'react';
import ApplicationReview from './ApplicationReview';
import CreateTenantModal from './CreateTenantModal';
import MembershipEditor from './MembershipEditor';

const t = (key: string) => dict(`PC.Pages.PlatformTenants.${/^[A-Z_]+$/.test(key) ? key.toLowerCase() : key.replace(/_([a-z])/g, (_, letter: string) => letter.toUpperCase())}`);

export default function PlatformTenants() {
  const [state, setState] = useState<
    'loading' | 'ready' | 'denied' | 'disabled' | 'error'
  >('loading');
  const [rows, setRows] = useState<TenantPolicyView[]>([]);
  const [selected, setSelected] = useState<TenantPolicyView>();
  const [saving, setSaving] = useState(false);
  const [membershipEnabled, setMembershipEnabled] = useState(false);
  const [canCreateTenant, setCanCreateTenant] = useState(false);
  const [creating, setCreating] = useState(false);
  const [memberTenant, setMemberTenant] = useState<number>();
  const [form] = Form.useForm<TenantPolicy & { reason: string }>();
  const plan = Form.useWatch('plan', form);

  const reload = async () => {
    setState('loading');
    try {
      const capabilities = await getPlatformCapabilities();
      setMembershipEnabled(capabilities.membershipEnabled === true);
      setCanCreateTenant(capabilities.canCreateTenant === true);
      if (!capabilities.platformAdmin) {
        setRows([]);
        setState('denied');
        return;
      }
      if (!capabilities.tenantPolicyEnabled) {
        setRows([]);
        setState('disabled');
        return;
      }
      setRows(await getPlatformTenants());
      setState('ready');
    } catch {
      setRows([]);
      setState('error');
    }
  };
  useEffect(() => {
    void reload();
  }, []);

  const edit = (row: TenantPolicyView) => {
    form.resetFields();
    form.setFieldsValue({ ...normalizeTenantPolicy(row.policy), reason: '' });
    setSelected(row);
  };
  const save = async () => {
    if (!selected || saving) return;
    let values;
    try {
      values = await form.validateFields();
    } catch {
      return;
    }
    setSaving(true);
    try {
      const updated = await updateTenantPolicy(
        selected.tenantId,
        selected.version,
        normalizeTenantPolicy(values),
        values.reason.trim(),
      );
      setRows((previous) =>
        previous.map((row) =>
          row.tenantId === updated.tenantId ? updated : row,
        ),
      );
      setSelected(undefined);
      message.success(t('saved'));
    } catch {
      message.error(t('saveFailed'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <WorkspaceLayout title={t('title')}>
      {state === 'ready' && (
        <Button href="/platform/portals">专用平台管理</Button>
      )}
      {state === 'ready' && <ApplicationReview />}
      <div style={{ padding: 24, width: '100%', minWidth: 0 }}>
        <Space style={{ marginBottom: 16 }}>
          {state === 'ready' && canCreateTenant && (
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setCreating(true)}
            >
              {t('createTenant')}
            </Button>
          )}
          <Button
            icon={<ReloadOutlined />}
            onClick={reload}
            disabled={state === 'loading'}
          >
            {t('refresh')}
          </Button>
        </Space>
        {state === 'loading' && <Spin />}
        {state === 'denied' && <Result status="403" title={t('denied')} />}
        {state === 'disabled' && (
          <Alert type="warning" message={t('disabled')} />
        )}
        {state === 'error' && <Alert type="error" message={t('loadFailed')} />}
        {state === 'ready' && (
          <>
            <Alert
              type="info"
              message={t('reserved')}
              style={{ marginBottom: 16 }}
            />
            <Table
              rowKey="tenantId"
              dataSource={rows}
              scroll={{ x: 680 }}
              columns={[
                { title: 'ID', dataIndex: 'tenantId', width: 90 },
                { title: t('name'), dataIndex: 'name' },
                { title: t('status'), dataIndex: 'status' },
                { title: t('plan'), render: (_, row) => t(row.policy.plan) },
                { title: t('version'), dataIndex: 'version' },
                {
                  title: t('members'),
                  render: (_, row) =>
                    membershipEnabled && (
                      <Button onClick={() => setMemberTenant(row.tenantId)}>
                        {t('members')}
                      </Button>
                    ),
                },
                {
                  title: t('edit'),
                  render: (_, row) => (
                    <Button icon={<EditOutlined />} onClick={() => edit(row)}>
                      {t('edit')}
                    </Button>
                  ),
                },
              ]}
            />
          </>
        )}
      </div>
      {creating && canCreateTenant && (
        <CreateTenantModal
          onClose={() => setCreating(false)}
          onCreated={() => {
            setCreating(false);
            void reload();
          }}
        />
      )}
      {memberTenant !== undefined && (
        <MembershipEditor
          key={memberTenant}
          tenantId={memberTenant}
          onClose={() => setMemberTenant(undefined)}
        />
      )}
      <Modal
        title={selected?.name}
        open={!!selected}
        onCancel={() => !saving && setSelected(undefined)}
        onOk={save}
        confirmLoading={saving}
        width={640}
        okText={t('save')}
        cancelText={t('cancel')}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="plan" label={t('plan')} rules={[{ required: true }]}>
            <Select
              options={['FREE', 'PAID'].map((value) => ({
                value,
                label: t(value),
              }))}
            />
          </Form.Item>
          {QUOTA_METRICS.map((metric) => (
            <Form.Item key={metric} label={t(metric)}>
              {plan === 'FREE' && metric === 'custom_domains' ? (
                <InputNumber value={0} disabled />
              ) : (
                <Space wrap>
                  <Form.Item name={['quotas', metric, 'mode']} noStyle>
                    <Select
                      style={{ width: 160 }}
                      options={['UNCONFIGURED', 'LIMITED', 'UNLIMITED'].map(
                        (value) => ({ value, label: t(value) }),
                      )}
                    />
                  </Form.Item>
                  <Form.Item noStyle shouldUpdate>
                    {() =>
                      form.getFieldValue(['quotas', metric, 'mode']) ===
                        'LIMITED' && (
                        <Form.Item
                          name={['quotas', metric, 'limit']}
                          noStyle
                          rules={[
                            {
                              validator: (_, value) =>
                                Number.isSafeInteger(value) && value >= 0
                                  ? Promise.resolve()
                                  : Promise.reject(
                                      new Error(t('invalidQuota')),
                                    ),
                            },
                          ]}
                        >
                          <InputNumber
                            min={0}
                            max={Number.MAX_SAFE_INTEGER}
                            precision={0}
                          />
                        </Form.Item>
                      )
                    }
                  </Form.Item>
                </Space>
              )}
            </Form.Item>
          ))}
          <Form.Item
            name="reason"
            label={t('reason')}
            rules={[{ required: true, whitespace: true, max: 500 }]}
          >
            <Input.TextArea maxLength={500} rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </WorkspaceLayout>
  );
}
