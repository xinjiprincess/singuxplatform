import { listPortals, savePortal, loadWebsiteBackgrounds, saveWebsiteBackgrounds } from '@/services/portal';
import { portalBackgroundImage, type PortalDefinition, type WebsiteBackgrounds } from '@/utils/portal';
import { EditOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import {
  Alert,
  Button,
  Form,
  Input,
  InputNumber,
  Modal,
  Space,
  Switch,
  Table,
  message,
} from 'antd';
import { useEffect, useState } from 'react';

function BackgroundFields() {
  return <>{(['loginBackground', 'workspaceBackground'] as const).map((field) => (
    <div key={field}>
      <Form.Item name={field} label={field === 'loginBackground' ? '登录页背景图路径' : '工作台及管理界面背景图路径'} rules={[{
        validator: (_, value) => !value || portalBackgroundImage(value)
          ? Promise.resolve() : Promise.reject(new Error('请填写 /logo/ 或 /api/file/ 下的站内图片路径')),
      }]}>
        <Input allowClear maxLength={500} />
      </Form.Item>
      <Form.Item noStyle shouldUpdate={(before, after) => before[field] !== after[field]}>
        {({ getFieldValue }) => portalBackgroundImage(getFieldValue(field)) ? (
          <img src={getFieldValue(field)} alt="背景预览" style={{ width: '100%', height: 100, objectFit: 'cover', marginBottom: 16 }} />
        ) : null}
      </Form.Item>
    </div>
  ))}</>;
}

export default function PlatformPortals() {
  const [website, setWebsite] = useState<WebsiteBackgrounds | null>(null);
  const [websiteForm] = Form.useForm();
  const [rows, setRows] = useState<PortalDefinition[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState<PortalDefinition | null | undefined>();
  const [form] = Form.useForm();
  const reload = async () => {
    setLoading(true);
    try {
      setRows(await listPortals());
      setError('');
    } catch (e) {
      setError(e instanceof Error ? e.message : '读取失败');
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    void reload();
  }, []);
  const edit = (row: PortalDefinition | null) => {
    form.resetFields();
    form.setFieldsValue(
      row || {
        slug: 'zhichuangbei',
        title: '2026华为智创杯·AI智能体开发大赛',
        subtitle: '智能体搭建与应用开发实践平台',
        accent: '#1677ff',
        enabled: false,
      },
    );
    setEditing(row);
  };
  const save = async () => {
    const { reason, ...portal } = await form.validateFields();
    portal.startsAt = portal.startsAt?.trim() || null;
    portal.endsAt = portal.endsAt?.trim() || null;
    setSaving(true);
    try {
      await savePortal(portal, editing || null, reason);
      setEditing(undefined);
      await reload();
      message.success('已保存');
    } catch (e) {
      message.error(e instanceof Error ? e.message : '保存失败');
    } finally {
      setSaving(false);
    }
  };
  const editWebsite = async () => {
    try {
      const value = await loadWebsiteBackgrounds();
      websiteForm.resetFields();
      websiteForm.setFieldsValue(value);
      setWebsite(value);
    } catch (e) { message.error(e instanceof Error ? e.message : '读取失败'); }
  };
  const saveWebsite = async () => {
    const { reason, ...backgrounds } = await websiteForm.validateFields();
    if (!website) return;
    setSaving(true);
    try {
      await saveWebsiteBackgrounds(backgrounds, website, reason);
      setWebsite(null);
      message.success('已保存，刷新页面后生效');
    } catch (e) { message.error(e instanceof Error ? e.message : '保存失败'); }
    finally { setSaving(false); }
  };
  return (
    <main style={{ padding: 24 }}>
      <h2>专用平台</h2>
      <Space>
        <Button icon={<EditOutlined />} onClick={editWebsite} disabled={!!error}>官网背景</Button>
        <Button icon={<ReloadOutlined />} onClick={reload}>
          刷新
        </Button>
        <Button
          icon={<PlusOutlined />}
          onClick={() => edit(null)}
          disabled={!!error}
        >
          创建入口
        </Button>
      </Space>
      {error && <Alert type="error" message={error} showIcon />}
      <Table
        rowKey="slug"
        loading={loading}
        dataSource={rows}
        columns={[
          {
            title: '入口',
            dataIndex: 'slug',
            render: (slug) => (
              <a href={`/${slug}/login`} target="_blank" rel="noreferrer">
                /{slug}
              </a>
            ),
          },
          { title: '名称', dataIndex: 'title' },
          { title: '企业 ID', dataIndex: 'tenantId' },
          {
            title: '启用',
            dataIndex: 'enabled',
            render: (value) => (value ? '是' : '否'),
          },
          {
            title: '操作',
            render: (_, row) => (
              <Button icon={<EditOutlined />} onClick={() => edit(row)}>
                编辑
              </Button>
            ),
          },
        ]}
      />
      <Modal
        title={editing ? '编辑专用平台' : '创建专用平台'}
        open={editing !== undefined}
        onCancel={() => !saving && setEditing(undefined)}
        onOk={save}
        confirmLoading={saving}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="slug"
            label="入口代号"
            rules={[{ required: true, pattern: /^[a-z][a-z0-9-]{2,39}$/ }]}
          >
            <Input disabled={!!editing} />
          </Form.Item>
          <Form.Item
            name="tenantId"
            label="企业 ID"
            rules={[{ required: true }]}
          >
            <InputNumber min={1} precision={0} disabled={!!editing} />
          </Form.Item>
          <Form.Item name="title" label="名称" rules={[{ required: true }]}>
            <Input maxLength={120} />
          </Form.Item>
          <Form.Item
            name="subtitle"
            label="副标题"
            rules={[{ required: true }]}
          >
            <Input maxLength={240} />
          </Form.Item>
          <Form.Item name="logo" label="Logo 路径">
            <Input />
          </Form.Item>
          <Form.Item name="favicon" label="标签图标路径">
            <Input />
          </Form.Item>
          <BackgroundFields />
          <Form.Item name="accent" label="主题色" rules={[{ required: true }]}>
            <Input type="color" />
          </Form.Item>
          <Form.Item name="startsAt" label="开始时间（ISO 8601）">
            <Input />
          </Form.Item>
          <Form.Item name="endsAt" label="结束时间（ISO 8601）">
            <Input />
          </Form.Item>
          <Form.Item name="enabled" label="启用" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item
            name="reason"
            label="变更原因"
            rules={[{ required: true }]}
          >
            <Input.TextArea maxLength={500} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal title="官网背景" open={website !== null} onCancel={() => !saving && setWebsite(null)} onOk={saveWebsite} confirmLoading={saving}>
        <Form form={websiteForm} layout="vertical">
          <BackgroundFields />
          <Form.Item name="reason" label="变更原因" rules={[{ required: true }]}><Input.TextArea maxLength={500} /></Form.Item>
        </Form>
      </Modal>
    </main>
  );
}
