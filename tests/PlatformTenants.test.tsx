import { cleanup, render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
vi.mock('@/services/tenantMembership', () => ({
  getPlatformMembers: vi.fn(), updatePlatformMember: vi.fn(),
}));
vi.mock('umi', () => ({ request: vi.fn() }));
vi.mock('@/services/tenantOnboarding', () => ({ getOnboarding: vi.fn().mockResolvedValue({ enabled: false }) }));
import PlatformTenants from '../src/pages/PlatformTenants';
const api = vi.hoisted(() => ({ capabilities: vi.fn(), list: vi.fn(), create: vi.fn() }));
vi.mock('@/services/tenantPolicy', () => ({
  getPlatformCapabilities: api.capabilities,
  getPlatformTenants: api.list,
  updateTenantPolicy: vi.fn(),
  createPlatformTenant: api.create,
}));
vi.mock('@/services/i18nRuntime', () => ({
  dict: (key: string) => key.split('.').pop(),
}));
vi.mock('@/components/WorkspaceLayout', () => ({
  default: ({ children }: React.PropsWithChildren) => <main>{children}</main>,
}));
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});
describe('platform access gate', () => {
  it('offers direct creation only with root provisioning capability', async () => {
    api.capabilities.mockResolvedValue({ platformAdmin: true, tenantPolicyEnabled: true, membershipEnabled: true, canCreateTenant: true });
    api.list.mockResolvedValue([]);
    render(<PlatformTenants />);
    expect(await screen.findByRole('button', { name: /createTenant/ })).toBeTruthy();
  });
  it('hides direct creation outside the root context', async () => {
    api.capabilities.mockResolvedValue({ platformAdmin: true, tenantPolicyEnabled: true, canCreateTenant: false });
    api.list.mockResolvedValue([]);
    render(<PlatformTenants />);
    await waitFor(() => expect(api.list).toHaveBeenCalled());
    expect(screen.queryByRole('button', { name: 'createTenant' })).toBeNull();
  });
  it('does not query tenant data for ordinary administrators', async () => {
    api.capabilities.mockResolvedValue({
      platformAdmin: false,
      tenantPolicyEnabled: true,
    });
    render(<PlatformTenants />);
    expect(await screen.findByText('denied')).toBeTruthy();
    expect(api.list).not.toHaveBeenCalled();
  });
  it('does not query disabled policy tables', async () => {
    api.capabilities.mockResolvedValue({
      platformAdmin: true,
      tenantPolicyEnabled: false,
    });
    render(<PlatformTenants />);
    expect(await screen.findByText('disabled')).toBeTruthy();
    expect(api.list).not.toHaveBeenCalled();
  });
  it('shows request failure rather than empty success', async () => {
    api.capabilities.mockRejectedValue(new Error('offline'));
    render(<PlatformTenants />);
    await waitFor(() => expect(screen.getByText('loadFailed')).toBeTruthy());
  });
});
