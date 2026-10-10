import { dict } from '@/services/i18nRuntime';
import {
  createPlatformTenant,
  type TenantCreateInput,
} from '@/services/tenantPolicy';
import { Form, Input, InputNumber, Modal, message } from 'antd';
import { useState } from 'react';

const t = (key: string) => dict(`PC.Pages.PlatformTenants.${key}`);
export default function CreateTenantModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [form] = Form.useForm<TenantCreateInput>();
  const [saving, setSaving] = useState(false);
  const save = async () => {
    if (saving) return;
    let input;
    try {
      input = await form.validateFields();
    } catch {
      return;
    }
    setSaving(true);
    try {
      await createPlatformTenant({
        ...input,
        name: input.name.trim(),
        reason: input.reason.trim(),
      });
      message.success(t('created'));
      onCreated();
    } catch (error) {
      message.error(error instanceof Error ? error.message : t('saveFailed'));
    } finally {
      setSaving(false);
    }
  };
  return (
    <Modal
      open
      title={t('createTenant')}
      onOk={save}
      confirmLoading={saving}
      onCancel={() => !saving && onClose()}
      maskClosable={!saving}
      okText={t('createTenant')}
      cancelText={t('cancel')}
    >
      <Form form={form} layout="vertical">
        <Form.Item
          name="name"
          label={t('name')}
          rules={[{ required: true, whitespace: true, max: 120 }]}
        >
          <Input maxLength={120} />
        </Form.Item>
        <Form.Item
          name="ownerUserId"
          label={t('ownerUserId')}
          rules={[
            { required: true },
            {
              validator: (_, value) =>
                Number.isSafeInteger(value) && value > 0
                  ? Promise.resolve()
                  : Promise.reject(new Error(t('ownerUserId'))),
            },
          ]}
        >
          <InputNumber min={1} precision={0} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item
          name="description"
          label={t('description')}
          rules={[{ max: 1000 }]}
        >
          <Input.TextArea maxLength={1000} rows={3} />
        </Form.Item>
        <Form.Item
          name="reason"
          label={t('reason')}
          rules={[{ required: true, whitespace: true, max: 500 }]}
        >
          <Input.TextArea maxLength={500} rows={2} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
