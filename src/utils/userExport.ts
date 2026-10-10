import type { SystemUserListInfo } from '@/types/interfaces/systemManage';

export const USER_EXPORT_FIELDS = [
  'id',
  'userName',
  'nickName',
  'email',
  'phone',
  'role',
  'status',
  'created',
] as const;

export function usersToCsv(
  users: SystemUserListInfo[],
  headers: string[],
): string {
  const cell = (value: unknown) => {
    let text = String(value ?? '');
    // Neutralize spreadsheet formulas, including values with leading whitespace.
    if (/^[\s\uFEFF]*[=+\-@]/.test(text) || /^[\t\r\n]/.test(text))
      text = `'${text}`;
    return `"${text.replace(/"/g, '""')}"`;
  };
  return (
    '\uFEFF' +
    [
      headers,
      ...users.map((user) => USER_EXPORT_FIELDS.map((key) => user[key])),
    ]
      .map((row) => row.map(cell).join(','))
      .join('\r\n')
  );
}
