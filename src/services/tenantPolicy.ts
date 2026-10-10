import type { RequestResponse } from '@/types/interfaces/request';
import type {
  TenantPolicy,
  TenantPolicyView,
} from '@/types/interfaces/tenantPolicy';
import { request } from 'umi';

async function unwrap<T>(result: Promise<RequestResponse<T>>): Promise<T> {
  const response = await result;
  if (response.code !== '0000')
    throw new Error(response.message || response.code);
  return response.data;
}
export const getPlatformCapabilities = () =>
  unwrap<{
    platformAdmin: boolean;
    tenantPolicyEnabled: boolean;
    membershipEnabled?: boolean;
    canCreateTenant?: boolean;
  }>(request('/api/platform/capabilities'));
export const getPlatformTenants = () =>
  unwrap<TenantPolicyView[]>(request('/api/platform/tenants'));
export interface TenantCreateInput {
  name: string;
  description?: string;
  ownerUserId: number;
  reason: string;
}
export const createPlatformTenant = (data: TenantCreateInput) =>
  unwrap<TenantPolicyView>(
    request('/api/platform/tenants', { method: 'POST', data }),
  );
export const updateTenantPolicy = (
  id: number,
  version: number,
  policy: TenantPolicy,
  reason: string,
) =>
  unwrap<TenantPolicyView>(
    request(`/api/platform/tenants/${id}/policy`, {
      method: 'PUT',
      data: { version, policy, reason },
    }),
  );
export const getCurrentTenantProfile = () =>
  unwrap<{ tenantId: number; name: string; status: string }>(
    request('/api/tenant/profile'),
  );
