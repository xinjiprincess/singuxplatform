import { dict } from '@/services/i18nRuntime';
import {
  getMyApplications,
  saveOrganization,
  searchEnterprises,
  submitEnterpriseApplication,
  type EnterpriseApplication,
  type OrganizationProfile,
} from '@/services/tenantOnboarding';
import {
  Alert,
  AutoComplete,
  Button,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Typography,
  message,
} from 'antd';
import { useEffect, useRef, useState } from 'react';

export default function Onboarding({
  profile,
  onSaved,
}: {
  profile: OrganizationProfile | null;
  onSaved: () => void;
}) {
  const [form] = Form.useForm();
  const [application] = Form.useForm();
  const [rows, setRows] = useState<EnterpriseApplication[]>([]);
  const [options, setOptions] = useState<
    { value: string; label: string; tenantId: number }[]
  >([]);
  const [target, setTarget] = useState<number>();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const generation = useRef(0);
  const timer = useRef<ReturnType<typeof setTimeout>>();
  const refresh = () =>
    getMyApplications()
      .then(setRows)
      .catch(() =>
        message.error(dict('PC.Pages.EnterpriseOnboarding.loadFailed')),
      );
  useEffect(() => {
    void refresh();
    return () => {
      clearTimeout(timer.current);
      generation.current++;
    };
  }, []);
  const search = (query: string) => {
    setTarget(undefined);
    clearTimeout(timer.current);
    const epoch = ++generation.current;
    setOptions([]);
    if (query.trim().length < 2) return;
    timer.current = setTimeout(async () => {
      try {
        const result = await searchEnterprises(query);
        if (generation.current === epoch)
          setOptions(
            result.map((row) => ({
              value: row.tenantName,
              label: `${row.tenantName} (#${row.targetTenantId})`,
              tenantId: row.targetTenantId,
            })),
          );
      } catch {
        if (generation.current === epoch)
          message.error(dict('PC.Pages.EnterpriseOnboarding.searchFailed'));
      }
    }, 300);
  };
  const save = async () => {
    const values = await form.validateFields();
    setBusy(true);
    try {
      await saveOrganization(values);
      onSaved();
      message.success(dict('PC.Pages.EnterpriseOnboarding.saved'));
    } catch (error) {
      message.error(
        error instanceof Error
          ? error.message
          : dict('PC.Pages.EnterpriseOnboarding.saveFailed'),
      );
    } finally {
      setBusy(false);
    }
  };
  const submit = async () => {
    const values = await application.validateFields();
    setBusy(true);
    try {
      await submitEnterpriseApplication({ ...values, targetTenantId: target });
      setOpen(false);
      await refresh();
    } catch (error) {
      message.error(
        error instanceof Error
          ? error.message
          : dict('PC.Pages.EnterpriseOnboarding.submitFailed'),
      );
    } finally {
      setBusy(false);
    }
  };
  return (
    <Space direction="vertical" style={{ width: '100%' }}>
      {!profile && (
        <Form
          form={form}
          layout="vertical"
          initialValues={{ organizationType: 'COMPANY' }}
        >
          <Form.Item
            name="organizationType"
            label={dict('PC.Pages.EnterpriseOnboarding.organizationType')}
            rules={[{ required: true }]}
          >
            <Select
              options={[
                {
                  value: 'COMPANY',
                  label: dict('PC.Pages.EnterpriseOnboarding.company'),
                },
                {
                  value: 'SCHOOL',
                  label: dict('PC.Pages.EnterpriseOnboarding.school'),
                },
              ]}
            />
          </Form.Item>
          <Form.Item
            name="organizationName"
            label={dict('PC.Pages.EnterpriseOnboarding.organizationName')}
            rules={[{ required: true, whitespace: true, max: 120 }]}
          >
            <AutoComplete options={options} onSearch={search}>
              <Input maxLength={120} />
            </AutoComplete>
          </Form.Item>
          <Button
            type="primary"
            onClick={() => void save().catch(() => {})}
            loading={busy}
          >
            {dict('PC.Pages.EnterpriseOnboarding.save')}
          </Button>
        </Form>
      )}
      {profile && (
        <>
          <Typography.Text>{profile.organizationName}</Typography.Text>
          <Button
            disabled={rows.some((row) => row.status === 'PENDING')}
            onClick={() => {
              application.resetFields();
              setTarget(undefined);
              setOptions([]);
              setOpen(true);
            }}
          >
            {dict('PC.Pages.EnterpriseOnboarding.apply')}
          </Button>
        </>
      )}
      {rows.map((row) => (
        <Alert
          key={row.id}
          type={
            row.status === 'APPROVED'
              ? 'success'
              : row.status === 'REJECTED'
              ? 'error'
              : 'info'
          }
          message={`${row.tenantName}：${
            {
              PENDING: dict('PC.Pages.EnterpriseOnboarding.pending'),
              APPROVED: dict('PC.Pages.EnterpriseOnboarding.approved'),
              REJECTED: dict('PC.Pages.EnterpriseOnboarding.rejected'),
            }[row.status]
          }`}
          description={row.reviewReason}
        />
      ))}
      <Modal
        title={
          target
            ? dict('PC.Pages.EnterpriseOnboarding.joinTitle')
            : dict('PC.Pages.EnterpriseOnboarding.createTitle')
        }
        open={open}
        onCancel={() => setOpen(false)}
        onOk={() => void submit().catch(() => {})}
        confirmLoading={busy}
        destroyOnClose
      >
        <Form form={application} layout="vertical">
          <Form.Item
            name="tenantName"
            label={dict('PC.Pages.EnterpriseOnboarding.enterprise')}
            rules={[{ required: true, whitespace: true, max: 120 }]}
          >
            <AutoComplete
              options={options}
              onSearch={search}
              onSelect={(_, option) => setTarget(option.tenantId)}
            >
              <Input maxLength={120} />
            </AutoComplete>
          </Form.Item>
          <Form.Item
            name="contactName"
            label={dict('PC.Pages.EnterpriseOnboarding.contactName')}
            rules={[{ required: true, whitespace: true, max: 80 }]}
          >
            <Input maxLength={80} />
          </Form.Item>
          <Form.Item
            name="contact"
            label={dict('PC.Pages.EnterpriseOnboarding.contact')}
            rules={[{ required: true, whitespace: true, max: 160 }]}
          >
            <Input maxLength={160} />
          </Form.Item>
          <Form.Item
            name="description"
            label={dict('PC.Pages.EnterpriseOnboarding.description')}
            rules={[{ required: true, whitespace: true, max: 1000 }]}
          >
            <Input.TextArea maxLength={1000} showCount />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
}
