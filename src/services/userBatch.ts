import type { RequestResponse } from '@/types/interfaces/request';
import type { BatchResult, BatchUserInput } from '@/types/interfaces/userBatch';
import { request } from 'umi';
export type { BatchResult, BatchUserInput } from '@/types/interfaces/userBatch';
async function post(url: string, data: unknown): Promise<BatchResult[]> {
  const result: RequestResponse<BatchResult[]> = await request(url, {
    method: 'POST',
    data,
  });
  if (result.code !== '0000') throw new Error(result.message || result.code);
  return result.data;
}
export const createUsersBatch = (users: BatchUserInput[]) =>
  post('/api/system/user/batch/add', { users });
export const setUsersBatchStatus = (ids: number[], enabled: boolean) =>
  post(`/api/system/user/batch/${enabled ? 'enable' : 'disable'}`, { ids });
export const updateMembersBatch = (
  tenantId: number,
  members: { userId: number; role: string; status: string; version: number }[],
  reason: string,
) =>
  post(`/api/platform/tenants/${tenantId}/members/batch`, { members, reason });
