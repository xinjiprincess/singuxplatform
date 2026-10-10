import { beforeEach, describe, expect, it, vi } from 'vitest';
import { apiSystemUserList } from '../src/services/systemManage';
import { getUsersForExport } from '../src/services/userExport';
import { usersToCsv } from '../src/utils/userExport';
vi.mock('../src/services/systemManage', () => ({ apiSystemUserList: vi.fn() }));
beforeEach(() => vi.clearAllMocks());
describe('user export', () => {
  it('exports only allowed fields and escapes formulas and quotes', () => {
    const csv = usersToCsv(
      [
        {
          id: 1,
          userName: ' =1+1',
          nickName: 'a,"b\nc',
          password: 'SECRET',
          token: 'TOKEN',
        } as any,
      ],
      ['ID'],
    );
    expect(csv.startsWith('\uFEFF')).toBe(true);
    expect(csv).toContain('"\' =1+1"');
    expect(csv).toContain('"a,""b\nc"');
    expect(csv).not.toContain('SECRET');
    expect(csv).not.toContain('TOKEN');
  });
  it('fetches all pages with the same filters', async () => {
    vi.mocked(apiSystemUserList)
      .mockResolvedValueOnce({
        code: '0000',
        data: { records: [{ id: 1 }], total: 2 },
      } as any)
      .mockResolvedValueOnce({
        code: '0000',
        data: { records: [{ id: 2 }], total: 2 },
      } as any);
    expect(await getUsersForExport({ role: 'Admin' })).toHaveLength(2);
    expect(apiSystemUserList).toHaveBeenLastCalledWith({
      pageNo: 2,
      pageSize: 100,
      queryFilter: { role: 'Admin' },
    });
  });
  it('does not silently export a partial list on error', async () => {
    vi.mocked(apiSystemUserList).mockResolvedValue({ code: 'DENIED' } as any);
    await expect(getUsersForExport({})).rejects.toThrow();
  });
  it('rejects excessive exports', async () => {
    vi.mocked(apiSystemUserList).mockResolvedValue({
      code: '0000',
      data: { records: [], total: 10001 },
    } as any);
    await expect(getUsersForExport({})).rejects.toThrow();
  });
  it('rejects duplicates caused by concurrent list changes', async () => {
    vi.mocked(apiSystemUserList).mockResolvedValue({
      code: '0000',
      data: { records: [{ id: 1 }], total: 2 },
    } as any);
    await expect(getUsersForExport({})).rejects.toThrow();
  });
});
