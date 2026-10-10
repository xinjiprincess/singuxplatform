import { request } from 'umi';
import { describe, expect, it, vi } from 'vitest';
import {
  getMyEnterprises,
  switchEnterprise,
} from '../src/services/tenantMembership';
vi.mock('umi', () => ({ request: vi.fn() }));
describe('enterprise switching API', () => {
  it('does not send a client-selected user identity', async () => {
    vi.mocked(request).mockResolvedValue({ code: '0000', data: [] });
    await getMyEnterprises();
    expect(request).toHaveBeenLastCalledWith('/api/me/tenants');
  });
  it('never accepts denied switching as a successful session', async () => {
    vi.mocked(request).mockResolvedValue({
      code: 'MEMBERSHIP_REQUIRED',
      message: 'Denied',
    });
    await expect(switchEnterprise(2)).rejects.toThrow('Denied');
  });
});
