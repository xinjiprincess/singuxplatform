import { dict } from '@/services/i18nRuntime';
import {
  getPlatformMembers,
  updatePlatformMember,
  type Membership,
} from '@/services/tenantMembership';
import { updateMembersBatch } from '@/services/userBatch';
import { downloadBatchJson } from '@/utils/userBatch';
import { EditOutlined } from '@ant-design/icons';
import {
  Alert,
  Button,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Space,
  Table,
  message,
} from 'antd';
import { useEffect, useState } from 'react';
const t = (key: string) => dict(`PC.Pages.MyEnterprises.${/^[A-Z]+$/.test(key) ? key.toLowerCase() : key}`);
export default function MembershipEditor({
  tenantId,
  onClose,
}: {
  tenantId: number;
  onClose: () => void;
}) {
  const [members, setMembers] = useState<Membership[]>([]);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [saving, setSaving] = useState(false);
  const [selectedIds, setSelectedIds] = useState<React.Key[]>([]);
  const [batchReason, setBatchReason] = useState('');
  const batch = (status: 'ACTIVE' | 'REVOKED') =>
    Modal.confirm({
      title: dict(
        status === 'ACTIVE'
          ? 'PC.Pages.UserBatch.restoreMembers'
          : 'PC.Pages.UserBatch.removeMembers',
      ),
      onOk: async () => {
        setSaving(true);
        try {
          const result = await updateMembersBatch(
            tenantId,
            members
              .filter((row) => selectedIds.includes(row.userId))
              .map((row) => ({
                userId: row.userId,
                role: row.role,
                version: row.version,
                status,
              })),
            batchReason.trim(),
          );
          const failures = result.filter((row) => !row.success);
          setSelectedIds(
            failures.flatMap((row) => (row.id === null ? [] : [row.id])),
          );
          if (failures.length) {
            downloadBatchJson(failures, 'singux-membership-failures.json');
            message.warning(dict('PC.Pages.UserBatch.partialFailure'));
          }
          setMembers(await getPlatformMembers(tenantId));
        } catch {
          message.error(t('failed'));
        } finally {
          setSaving(false);
        }
      },
    });
  const [form] = Form.useForm();
  useEffect(() => {
    let active = true;
    getPlatformMembers(tenantId)
      .then((rows) => {
        if (active) setMembers(rows);
      })
      .catch(() => {
        if (active) setFailed(true);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [tenantId]);
  const save = async () => {
    let values;
    try {
      values = await form.validateFields();
    } catch {
      return;
    }
    setSaving(true);
    try {
      const previous = members.find(
        (member) => member.userId === values.userId,
      );
      const updated = await updatePlatformMember(tenantId, values.userId, {
        role: values.role,
        status: values.status,
        reason: values.reason.trim(),
        version: previous?.version ?? -1,
      });
      setMembers((rows) => [
        ...rows.filter((row) => row.userId !== updated.userId),
        updated,
      ]);
      form.resetFields();
    } catch {
      message.error(t('failed'));
    } finally {
      setSaving(false);
    }
  };
  return (
    <Modal
      open
      title={t('members')}
      width={760}
      onCancel={() => !saving && onClose()}
      onOk={save}
      confirmLoading={saving}
      okButtonProps={{ disabled: loading || failed }}
      okText={t('save')}
      cancelText={t('cancel')}
    >
      {failed && <Alert type="error" message={t('failed')} />}
      <Space wrap style={{ marginBottom: 12 }}>
        <Input
          aria-label={t('reason')}
          placeholder={t('reason')}
          value={batchReason}
          maxLength={500}
          disabled={saving}
          onChange={(event) => setBatchReason(event.target.value)}
        />
        <Button
          danger
          disabled={
            saving ||
            !selectedIds.length ||
            selectedIds.length > 200 ||
            !batchReason.trim()
          }
          onClick={() => batch('REVOKED')}
        >
          {dict('PC.Pages.UserBatch.removeMembers')}
        </Button>
        <Button
          disabled={
            saving ||
            !selectedIds.length ||
            selectedIds.length > 200 ||
            !batchReason.trim()
          }
          onClick={() => batch('ACTIVE')}
        >
          {dict('PC.Pages.UserBatch.restoreMembers')}
        </Button>
      </Space>
      <Table
        loading={loading}
        rowKey="userId"
        dataSource={members}
        rowSelection={{
          selectedRowKeys: selectedIds,
          onChange: setSelectedIds,
          getCheckboxProps: () => ({ disabled: saving || loading || failed }),
        }}
        pagination={{
          defaultPageSize: 20,
          showSizeChanger: true,
          pageSizeOptions: [20, 50, 100, 200],
        }}
        size="small"
        scroll={{ x: 500 }}
        columns={[
          { title: 'ID', dataIndex: 'userId' },
          { title: t('name'), dataIndex: 'name' },
          { title: t('role'), dataIndex: 'role', render: (role) => t(role) },
          {
            title: t('status'),
            dataIndex: 'status',
            render: (status) => t(status),
          },
          {
            title: t('edit'),
            render: (_, row) => (
              <Button
                icon={<EditOutlined />}
                onClick={() =>
                  form.setFieldsValue({
                    userId: row.userId,
                    role: row.role,
                    status: row.status,
                    reason: '',
                  })
                }
              >
                {t('edit')}
              </Button>
            ),
          },
        ]}
      />
      <Form
        form={form}
        layout="vertical"
        initialValues={{ role: 'MEMBER', status: 'ACTIVE' }}
      >
        <Form.Item
          name="userId"
          label={t('userId')}
          rules={[
            { required: true },
            {
              validator: (_, value) =>
                Number.isSafeInteger(value) && value > 0
                  ? Promise.resolve()
                  : Promise.reject(new Error(t('userId'))),
            },
          ]}
        >
          <InputNumber min={1} precision={0} />
        </Form.Item>
        <Form.Item name="role" label={t('role')} rules={[{ required: true }]}>
          <Select
            options={['OWNER', 'ADMIN', 'MEMBER'].map((value) => ({
              value,
              label: t(value),
            }))}
          />
        </Form.Item>
        <Form.Item
          name="status"
          label={t('status')}
          rules={[{ required: true }]}
        >
          <Select
            options={['ACTIVE', 'REVOKED'].map((value) => ({
              value,
              label: t(value),
            }))}
          />
        </Form.Item>
        <Form.Item
          name="reason"
          label={t('reason')}
          rules={[{ required: true, whitespace: true, max: 500 }]}
        >
          <Input.TextArea maxLength={500} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
