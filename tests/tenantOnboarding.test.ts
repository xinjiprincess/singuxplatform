import { request } from 'umi';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  getOnboarding,
  reviewEnterpriseApplication,
  saveOrganization,
  searchEnterprises,
  submitEnterpriseApplication,
} from '../src/services/tenantOnboarding';
vi.mock('umi', () => ({ request: vi.fn() }));
describe('enterprise onboarding API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(request).mockResolvedValue({ code: '0000', data: {} });
  });
  it('loads rollout and profile without a client user ID', async () => {
    await getOnboarding();
    expect(request).toHaveBeenCalledWith('/api/me/onboarding');
  });
  it('saves company information, not authorization', async () => {
    const profile = {
      organizationType: 'SCHOOL' as const,
      organizationName: 'Example school',
    };
    await saveOrganization(profile);
    expect(request).toHaveBeenCalledWith('/api/me/onboarding', {
      method: 'PUT',
      data: profile,
    });
  });
  it('keeps search text in query parameters', async () => {
    await searchEnterprises('A&B');
    expect(request).toHaveBeenCalledWith('/api/me/enterprise-search', {
      params: { query: 'A&B' },
    });
  });
  it('submits application without granting a role', async () => {
    const command = {
      tenantName: 'Enterprise',
      contactName: 'Name',
      contact: 'a@example.com',
      description: 'Application',
    };
    await submitEnterpriseApplication(command);
    expect(request).toHaveBeenCalledWith('/api/me/enterprise-applications', {
      method: 'POST',
      data: command,
    });
  });
  it('does not treat a rejected review request as success', async () => {
    vi.mocked(request).mockResolvedValue({
      code: 'SELF_REVIEW_DENIED',
      message: 'Denied',
    });
    await expect(
      reviewEnterpriseApplication(3, true, 'reason'),
    ).rejects.toThrow('Denied');
  });
});
