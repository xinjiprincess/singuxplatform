import type { RequestResponse } from '@/types/interfaces/request';
import { request } from 'umi';

export interface Membership {
  tenantId: number;
  userId: number;
  name: string;
  role: 'OWNER' | 'ADMIN' | 'MEMBER';
  status: 'ACTIVE' | 'REVOKED';
  version: number;
}
async function data<T>(promise: Promise<RequestResponse<T>>): Promise<T> {
  const result = await promise;
  if (result.code !== '0000') throw new Error(result.message || result.code);
  return result.data;
}
export const getMyEnterprises = () =>
  data<Membership[]>(request('/api/me/tenants'));
export const getEnterpriseMembers = () =>
  data<Membership[]>(request('/api/tenant/members'));
export const getPlatformMembers = (tenantId: number) =>
  data<Membership[]>(request(`/api/platform/tenants/${tenantId}/members`));
export const updatePlatformMember = (
  tenantId: number,
  userId: number,
  change: {
    role: Membership['role'];
    status: Membership['status'];
    version: number;
    reason: string;
  },
) =>
  data<Membership>(
    request(`/api/platform/tenants/${tenantId}/members/${userId}`, {
      method: 'PUT',
      data: change,
    }),
  );
// 初次选择企业：消费登录阶段签发的身份会话，签发企业会话。
// 与 switchEnterprise 的区别是调用方持有的会话类型不同（身份会话 vs 企业会话），
// 服务端两者都会重新校验企业状态和成员资格。
export const selectEnterprise = (tenantId: number) =>
  data<{ token: string; tenantId: number; expiresIn: number }>(
    request('/api/session/tenant/select', {
      method: 'POST',
      data: { tenantId },
    }),
  );
export const switchEnterprise = (tenantId: number) =>
  data<{ token: string; tenantId: number; expiresIn: number }>(
    request('/api/session/tenant/switch', {
      method: 'POST',
      data: { tenantId },
    }),
  );
