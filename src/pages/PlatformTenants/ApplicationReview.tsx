import { dict } from '@/services/i18nRuntime';
import {
  getEnterpriseApplications,
  getOnboarding,
  reviewEnterpriseApplication,
  type EnterpriseApplication,
} from '@/services/tenantOnboarding';
import {
  Button,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Table,
  message,
} from 'antd';
import { useEffect, useState } from 'react';

export default function ApplicationReview() {
  const [enabled, setEnabled] = useState(false);
  const [open, setOpen] = useState(false);
  const [rows, setRows] = useState<EnterpriseApplication[]>([]);
  const [selected, setSelected] = useState<EnterpriseApplication>();
  const [busy, setBusy] = useState(false);
  const [form] = Form.useForm();
  useEffect(() => {
    getOnboarding()
      .then((value) => setEnabled(value.enabled))
      .catch(() => {});
  }, []);
  const load = async (before?: number) => {
    setBusy(true);
    try {
      const page = await getEnterpriseApplications(before);
      setRows((previous) => (before ? [...previous, ...page] : page));
    } catch {
      message.error(dict('PC.Pages.EnterpriseOnboarding.queueFailed'));
    } finally {
      setBusy(false);
    }
  };
  const review = async () => {
    const values = await form.validateFields();
    if (!selected) return;
    setBusy(true);
    try {
      await reviewEnterpriseApplication(
        selected.id,
        values.approve === 'APPROVE',
        values.reason,
      );
      setSelected(undefined);
      await load();
    } catch (error) {
      message.error(
        error instanceof Error
          ? error.message
          : dict('PC.Pages.EnterpriseOnboarding.reviewFailed'),
      );
    } finally {
      setBusy(false);
    }
  };
  if (!enabled) return null;
  return (
    <>
      <Button
        onClick={() => {
          setOpen(true);
          void load();
        }}
      >
        {dict('PC.Pages.EnterpriseOnboarding.review')}
      </Button>
      <Modal
        title={dict('PC.Pages.EnterpriseOnboarding.queueTitle')}
        width={960}
        open={open}
        onCancel={() => setOpen(false)}
        footer={null}
      >
        <Table
          rowKey="id"
          dataSource={rows}
          loading={busy}
          scroll={{ x: 800 }}
          columns={[
            {
              title: dict('PC.Pages.EnterpriseOnboarding.enterpriseColumn'),
              dataIndex: 'tenantName',
            },
            {
              title: dict('PC.Pages.EnterpriseOnboarding.organizationColumn'),
              dataIndex: 'organizationName',
            },
            {
              title: dict('PC.Pages.EnterpriseOnboarding.type'),
              render: (_, row) =>
                row.targetTenantId
                  ? dict('PC.Pages.EnterpriseOnboarding.join')
                  : dict('PC.Pages.EnterpriseOnboarding.create'),
            },
            {
              title: dict('PC.Pages.EnterpriseOnboarding.contactName'),
              dataIndex: 'contactName',
            },
            {
              title: dict('PC.Pages.EnterpriseOnboarding.contactColumn'),
              dataIndex: 'contact',
            },
            {
              title: dict('PC.Pages.EnterpriseOnboarding.description'),
              dataIndex: 'description',
            },
            {
              title: dict('PC.Pages.EnterpriseOnboarding.status'),
              render: (_, row) =>
                ({
                  PENDING: dict('PC.Pages.EnterpriseOnboarding.pending'),
                  APPROVED: dict('PC.Pages.EnterpriseOnboarding.approved'),
                  REJECTED: dict('PC.Pages.EnterpriseOnboarding.rejected'),
                }[row.status]),
            },
            {
              title: dict('PC.Pages.EnterpriseOnboarding.reason'),
              dataIndex: 'reviewReason',
            },
            {
              title: dict('PC.Pages.EnterpriseOnboarding.actions'),
              render: (_, row) =>
                row.status === 'PENDING' && (
                  <Button
                    onClick={() => {
                      form.resetFields();
                      setSelected(row);
                    }}
                  >
                    {dict('PC.Pages.EnterpriseOnboarding.reviewAction')}
                  </Button>
                ),
            },
          ]}
        />
        <Space>
          <Button onClick={() => void load()}>
            {dict('PC.Pages.EnterpriseOnboarding.refresh')}
          </Button>
          {rows.length > 0 && (
            <Button onClick={() => void load(rows[rows.length - 1].id)}>
              {dict('PC.Pages.EnterpriseOnboarding.older')}
            </Button>
          )}
        </Space>
      </Modal>
      <Modal
        title={dict('PC.Pages.EnterpriseOnboarding.reviewTitle')}
        open={!!selected}
        onCancel={() => setSelected(undefined)}
        onOk={() => void review().catch(() => {})}
        confirmLoading={busy}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="approve"
            label={dict('PC.Pages.EnterpriseOnboarding.decision')}
            rules={[{ required: true }]}
          >
            <Select
              options={[
                {
                  value: 'APPROVE',
                  label: dict('PC.Pages.EnterpriseOnboarding.approve'),
                },
                {
                  value: 'REJECT',
                  label: dict('PC.Pages.EnterpriseOnboarding.reject'),
                },
              ]}
            />
          </Form.Item>
          <Form.Item
            name="reason"
            label={dict('PC.Pages.EnterpriseOnboarding.reason')}
            rules={[{ required: true, whitespace: true, max: 500 }]}
          >
            <Input.TextArea maxLength={500} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
