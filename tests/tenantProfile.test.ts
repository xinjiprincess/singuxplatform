import { request } from 'umi';
import { describe, expect, it, vi } from 'vitest';
import {
  getCurrentTenantProfile,
  updateTenantPolicy,
} from '../src/services/tenantPolicy';
vi.mock('umi', () => ({ request: vi.fn() }));

describe('tenant APIs', () => {
  it('loads the current server-selected tenant without a client tenant ID', async () => {
    vi.mocked(request).mockResolvedValue({
      code: '0000',
      data: { tenantId: 7, name: 'Enterprise' },
    });
    expect((await getCurrentTenantProfile()).tenantId).toBe(7);
    expect(request).toHaveBeenLastCalledWith('/api/tenant/profile');
  });
  it('does not disguise a failed request as a demo tenant', async () => {
    vi.mocked(request).mockResolvedValue({ code: 'DENIED', message: 'Denied' });
    await expect(getCurrentTenantProfile()).rejects.toThrow('Denied');
  });
  it('sends the optimistic version and audit reason', async () => {
    vi.mocked(request).mockResolvedValue({ code: '0000', data: {} });
    await updateTenantPolicy(7, 3, { plan: 'FREE', quotas: {} }, 'Change');
    expect(request).toHaveBeenLastCalledWith('/api/platform/tenants/7/policy', {
      method: 'PUT',
      data: {
        version: 3,
        policy: { plan: 'FREE', quotas: {} },
        reason: 'Change',
      },
    });
  });
});
