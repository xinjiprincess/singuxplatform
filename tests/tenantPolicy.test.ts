import { describe, expect, it } from 'vitest';
import { normalizeTenantPolicy } from '../src/utils/tenantPolicy';

describe('enterprise quota configuration', () => {
  it('never enables custom domains for free plans', () => {
    const result = normalizeTenantPolicy({
      plan: 'FREE',
      quotas: { custom_domains: { mode: 'UNLIMITED', limit: null } },
    });
    expect(result.quotas.custom_domains).toEqual({ mode: 'LIMITED', limit: 0 });
  });
  it('preserves zero and distinguishes unconfigured from unlimited', () => {
    const result = normalizeTenantPolicy({
      plan: 'PAID',
      quotas: {
        members: { mode: 'LIMITED', limit: 0 },
        spaces: { mode: 'UNLIMITED', limit: null },
      },
    });
    expect(result.quotas.members?.limit).toBe(0);
    expect(result.quotas.spaces?.mode).toBe('UNLIMITED');
    expect(result.quotas.agents?.mode).toBe('UNCONFIGURED');
  });
  it.each([-1, 1.5, Number.MAX_SAFE_INTEGER + 1, null])(
    'rejects invalid limit %s',
    (limit) => {
      expect(() =>
        normalizeTenantPolicy({
          plan: 'PAID',
          quotas: { members: { mode: 'LIMITED', limit } },
        }),
      ).toThrow();
    },
  );
  it('does not mutate the source policy', () => {
    const policy = { plan: 'FREE' as const, quotas: {} };
    normalizeTenantPolicy(policy);
    expect(policy.quotas).toEqual({});
  });
});
