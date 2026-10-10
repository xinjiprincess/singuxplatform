import {
  QUOTA_METRICS,
  type TenantPolicy,
} from '@/types/interfaces/tenantPolicy';

export function normalizeTenantPolicy(policy: TenantPolicy): TenantPolicy {
  const quotas: TenantPolicy['quotas'] = {};
  for (const metric of QUOTA_METRICS) {
    const quota = policy.quotas[metric] || {
      mode: 'UNCONFIGURED',
      limit: null,
    };
    if (metric === 'custom_domains' && policy.plan === 'FREE') {
      quotas[metric] = { mode: 'LIMITED', limit: 0 };
    } else if (quota.mode === 'LIMITED') {
      if (
        quota.limit === null ||
        !Number.isSafeInteger(quota.limit) ||
        quota.limit < 0
      ) {
        throw new Error('INVALID_QUOTA');
      }
      quotas[metric] = { ...quota };
    } else {
      quotas[metric] = { mode: quota.mode, limit: null };
    }
  }
  return { plan: policy.plan, quotas };
}
