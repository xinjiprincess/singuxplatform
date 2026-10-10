import type { BatchUserInput } from '@/types/interfaces/userBatch';

export function parseBatchUsers(text: string): BatchUserInput[] {
  const value: unknown = JSON.parse(text.replace(/^\uFEFF/, ''));
  if (!Array.isArray(value) || value.length < 1 || value.length > 200)
    throw new Error('INVALID_BATCH');
  const fields = [
    'uid',
    'userName',
    'nickName',
    'email',
    'phone',
    'password',
  ] as const;
  return value.map((row) => {
    if (
      !row ||
      typeof row !== 'object' ||
      Array.isArray(row) ||
      Object.keys(row).some(
        (key) => !fields.includes(key as (typeof fields)[number]),
      ) ||
      fields.some((key) => row[key] != null && typeof row[key] !== 'string') ||
      typeof row.userName !== 'string' ||
      typeof row.password !== 'string'
    )
      throw new Error('INVALID_USER');
    return Object.fromEntries(
      fields.filter((key) => row[key] != null).map((key) => [key, row[key]]),
    ) as unknown as BatchUserInput;
  });
}

export function downloadBatchJson(value: unknown, name: string) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' }),
  );
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = name;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}
