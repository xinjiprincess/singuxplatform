import { dict } from '@/services/i18nRuntime';
import {
  createUsersBatch,
  type BatchResult,
  type BatchUserInput,
} from '@/services/userBatch';
import { downloadBatchJson, parseBatchUsers } from '@/utils/userBatch';
import {
  DeleteOutlined,
  DownloadOutlined,
  PlusOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import {
  Alert,
  Button,
  Input,
  Modal,
  Space,
  Table,
  Upload,
  message,
} from 'antd';
import { useState } from 'react';

const t = (key: string) => dict(`PC.Pages.UserBatch.${key}`);
const fields = ['userName', 'nickName', 'email', 'phone', 'password'] as const;
export default function BatchUsersModal({
  onClose,
  onChanged,
}: {
  onClose: () => void;
  onChanged: () => void;
}) {
  const [rows, setRows] = useState<(BatchUserInput & { key: string })[]>([
    { key: crypto.randomUUID(), userName: '', password: '' },
  ]);
  const [results, setResults] = useState<BatchResult[]>([]);
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    if (busy || !rows.length) return;
    setBusy(true);
    try {
      const result = await createUsersBatch(
        rows.map(({ key: _, ...row }) => row),
      );
      setResults(result);
      const failed = new Set(
        result.filter((row) => !row.success).map((row) => row.row - 1),
      );
      setRows((previous) => previous.filter((_, index) => failed.has(index)));
      onChanged();
    } catch (error) {
      message.error(error instanceof Error ? error.message : t('failed'));
    } finally {
      setBusy(false);
    }
  };
  return (
    <Modal
      open
      width={1000}
      title={t('add')}
      onCancel={() => !busy && onClose()}
      maskClosable={!busy}
      footer={
        <Space wrap>
          <Button disabled={busy} onClick={onClose}>
            {t('close')}
          </Button>
          <Button
            type="primary"
            disabled={!rows.length}
            loading={busy}
            onClick={submit}
          >
            {t('importAll')}
          </Button>
        </Space>
      }
    >
      <Space wrap style={{ marginBottom: 16 }}>
        <Button
          icon={<PlusOutlined />}
          disabled={busy || rows.length >= 200}
          onClick={() =>
            setRows([
              ...rows,
              { key: crypto.randomUUID(), userName: '', password: '' },
            ])
          }
        >
          {t('addRow')}
        </Button>
        <Upload
          accept=".json"
          showUploadList={false}
          disabled={busy}
          beforeUpload={async (file) => {
            try {
              if (file.size > 1024 * 1024) throw new Error('FILE_TOO_LARGE');
              const parsed = parseBatchUsers(await file.text());
              setRows(
                parsed.map((row) => ({ ...row, key: crypto.randomUUID() })),
              );
              setResults([]);
            } catch {
              message.error(t('invalidFile'));
            }
            return false;
          }}
        >
          <Button icon={<UploadOutlined />} disabled={busy}>
            {t('importJson')}
          </Button>
        </Upload>
        <Button
          icon={<DownloadOutlined />}
          disabled={busy}
          onClick={() =>
            downloadBatchJson(
              [
                {
                  userName: 'cdut20260001',
                  nickName: '',
                  email: 'student@example.com',
                  phone: '',
                  password: '',
                },
              ],
              'singux-user-template.json',
            )
          }
        >
          {t('template')}
        </Button>
      </Space>
      <Table
        size="small"
        rowKey="key"
        dataSource={rows}
        scroll={{ x: 880, y: 320 }}
        pagination={{
          defaultPageSize: 20,
          showSizeChanger: true,
          pageSizeOptions: [20, 50, 100, 200],
        }}
        columns={[
          ...fields.map((field) => ({
            title: t(field),
            dataIndex: field,
            width: field === 'email' ? 210 : 160,
            render: (value: string, row: BatchUserInput & { key: string }) =>
              field === 'password' ? (
                <Input.Password
                  aria-label={t(field)}
                  value={value}
                  disabled={busy}
                  onChange={(e) =>
                    setRows((previous) =>
                      previous.map((item) =>
                        item.key === row.key
                          ? { ...item, [field]: e.target.value }
                          : item,
                      ),
                    )
                  }
                />
              ) : (
                <Input
                  aria-label={t(field)}
                  value={value}
                  disabled={busy}
                  maxLength={field === 'email' ? 160 : 100}
                  onChange={(e) =>
                    setRows((previous) =>
                      previous.map((item) =>
                        item.key === row.key
                          ? { ...item, [field]: e.target.value }
                          : item,
                      ),
                    )
                  }
                />
              ),
          })),
          {
            title: t('remove'),
            width: 60,
            render: (_, row) => (
              <Button
                danger
                type="text"
                icon={<DeleteOutlined />}
                title={t('remove')}
                disabled={busy}
                onClick={() =>
                  setRows(rows.filter((item) => item.key !== row.key))
                }
              />
            ),
          },
        ]}
      />
      {!!results.length && (
        <>
          <Alert
            style={{ marginTop: 16 }}
            type={results.some((row) => !row.success) ? 'warning' : 'success'}
            message={`${t('success')}: ${
              results.filter((row) => row.success).length
            } / ${t('failed')}: ${
              results.filter((row) => !row.success).length
            }`}
          />
          <Button
            icon={<DownloadOutlined />}
            style={{ marginTop: 8 }}
            onClick={() =>
              downloadBatchJson(
                results.filter((row) => !row.success),
                'singux-user-failures.json',
              )
            }
          >
            {t('exportFailures')}
          </Button>
          <Table
            size="small"
            rowKey="row"
            dataSource={results}
            pagination={{ pageSize: 20 }}
            columns={[
              { title: t('row'), dataIndex: 'row' },
              { title: t('userName'), dataIndex: 'userName' },
              { title: t('result'), dataIndex: 'message' },
            ]}
          />
        </>
      )}
    </Modal>
  );
}
