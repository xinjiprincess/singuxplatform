import WorkspaceLayout from '@/components/WorkspaceLayout';
import { dict } from '@/services/i18nRuntime';
import {
  getMyEnterprises,
  switchEnterprise,
  type Membership,
} from '@/services/tenantMembership';
import { getPlatformCapabilities } from '@/services/tenantPolicy';
import { applyTenantSession } from '@/services/tenantSession';
import { ReloadOutlined, SwapOutlined } from '@ant-design/icons';
import { Alert, Button, Modal, Space, Spin, Table, message } from 'antd';
import { useEffect, useState } from 'react';

const t = (key: string) => dict(`PC.Pages.MyEnterprises.${/^[A-Z]+$/.test(key) ? key.toLowerCase() : key}`);
export default function MyEnterprises() {
  const [rows, setRows] = useState<Membership[]>([]);
  const [state, setState] = useState('loading');
  const [switching, setSwitching] = useState(false);
  const load = async () => {
    setState('loading');
    try {
      const capabilities = await getPlatformCapabilities();
      if (!capabilities.membershipEnabled) {
        setState('disabled');
        return;
      }
      setRows(await getMyEnterprises());
      setState('ready');
    } catch {
      setState('error');
    }
  };
  useEffect(() => {
    void load();
  }, []);
  const select = (row: Membership) =>
    Modal.confirm({
      title: t('confirm'),
      content: row.name,
      okText: t('switch'),
      cancelText: t('cancel'),
      onOk: async () => {
        setSwitching(true);
        try {
          applyTenantSession(await switchEnterprise(row.tenantId));
        } catch {
          message.error(t('failed'));
          setSwitching(false);
        }
      },
    });
  return (
    <WorkspaceLayout title={t('title')}>
      <div style={{ padding: 24 }}>
        <Space style={{ marginBottom: 16 }}>
          <Button
            icon={<ReloadOutlined />}
            disabled={switching || state === 'loading'}
            onClick={load}
          >
            {t('refresh')}
          </Button>
        </Space>
        {state === 'loading' && <Spin />}
        {state === 'disabled' && (
          <Alert type="warning" message={t('disabled')} />
        )}
        {state === 'error' && <Alert type="error" message={t('failed')} />}
        {state === 'ready' && (
          <Table
            rowKey="tenantId"
            dataSource={rows}
            scroll={{ x: 480 }}
            columns={[
              { title: t('enterprise'), dataIndex: 'name' },
              {
                title: t('role'),
                dataIndex: 'role',
                render: (role) => t(role),
              },
              {
                title: t('switch'),
                render: (_, row) => (
                  <Button
                    icon={<SwapOutlined />}
                    disabled={switching}
                    onClick={() => select(row)}
                  >
                    {t('switch')}
                  </Button>
                ),
              },
            ]}
          />
        )}
      </div>
    </WorkspaceLayout>
  );
}
