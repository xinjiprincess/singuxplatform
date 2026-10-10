export const QUOTA_METRICS = [
  'members',
  'spaces',
  'agents',
  'storage_bytes',
  'monthly_model_tokens',
  'monthly_requests',
  'concurrent_jobs',
  'custom_domains',
] as const;
export type QuotaMetric = (typeof QUOTA_METRICS)[number];
export interface Quota {
  mode: 'UNCONFIGURED' | 'LIMITED' | 'UNLIMITED';
  limit: number | null;
}
export interface TenantPolicy {
  plan: 'FREE' | 'PAID';
  quotas: Partial<Record<QuotaMetric, Quota>>;
}
export interface TenantPolicyView {
  tenantId: number;
  name: string;
  status: string;
  version: number;
  policy: TenantPolicy;
  customLogo: boolean;
  customDomain: boolean;
  quotaEnforcementEnabled: boolean;
}
