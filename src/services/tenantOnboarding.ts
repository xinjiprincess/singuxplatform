import type { RequestResponse } from '@/types/interfaces/request';
import { request } from 'umi';

export interface OrganizationProfile {
  organizationType: 'COMPANY' | 'SCHOOL';
  organizationName: string;
}
export interface EnterpriseApplication extends OrganizationProfile {
  id: number;
  tenantName: string;
  targetTenantId?: number;
  contactName: string;
  contact: string;
  description: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  reviewReason?: string;
}
async function data<T>(promise: Promise<RequestResponse<T>>): Promise<T> {
  const result = await promise;
  if (result.code !== '0000') throw new Error(result.message || result.code);
  return result.data;
}
export const getOnboarding = () =>
  data<{ enabled: boolean; profile: OrganizationProfile | null }>(
    request('/api/me/onboarding'),
  );
export const saveOrganization = (profile: OrganizationProfile) =>
  data(request('/api/me/onboarding', { method: 'PUT', data: profile }));
export const searchEnterprises = (query: string) =>
  data<{ targetTenantId: number; tenantName: string }[]>(
    request('/api/me/enterprise-search', { params: { query } }),
  );
export const getMyApplications = () =>
  data<EnterpriseApplication[]>(request('/api/me/enterprise-applications'));
export const submitEnterpriseApplication = (
  command: Pick<
    EnterpriseApplication,
    'tenantName' | 'targetTenantId' | 'contactName' | 'contact' | 'description'
  >,
) =>
  data(
    request('/api/me/enterprise-applications', {
      method: 'POST',
      data: command,
    }),
  );
export const getEnterpriseApplications = (before?: number) =>
  data<EnterpriseApplication[]>(
    request('/api/platform/enterprise-applications', { params: { before } }),
  );
export const reviewEnterpriseApplication = (
  id: number,
  approve: boolean,
  reason: string,
) =>
  data(
    request(`/api/platform/enterprise-applications/${id}/review`, {
      method: 'POST',
      data: { approve, reason },
    }),
  );
