import React from 'react';
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
const api = vi.hoisted(() => ({ capabilities: vi.fn(), list: vi.fn() }));
vi.mock('@/services/tenantPolicy', () => ({ getPlatformCapabilities: api.capabilities }));
vi.mock('@/services/tenantMembership', () => ({ getMyEnterprises: api.list, switchEnterprise: vi.fn() }));
vi.mock('@/services/tenantSession', () => ({ applyTenantSession: vi.fn() }));
vi.mock('@/services/i18nRuntime', () => ({ dict: (key: string) => key.split('.').pop() }));
vi.mock('@/components/WorkspaceLayout', () => ({ default: ({ children }: React.PropsWithChildren) => <main>{children}</main> }));
import MyEnterprises from '../src/pages/MyEnterprises';
afterEach(() => { cleanup(); vi.clearAllMocks(); });
describe('my enterprises', () => {
  it('does not fetch memberships when feature is disabled', async () => {
    api.capabilities.mockResolvedValue({ membershipEnabled: false });
    render(<MyEnterprises />);
    expect(await screen.findByText('disabled')).toBeTruthy();
    expect(api.list).not.toHaveBeenCalled();
  });
  it('renders only memberships returned by the server', async () => {
    api.capabilities.mockResolvedValue({ membershipEnabled: true });
    api.list.mockResolvedValue([{ tenantId: 7, userId: 9, name: 'Enterprise A', role: 'MEMBER', status: 'ACTIVE', version: 0 }]);
    render(<MyEnterprises />);
    expect(await screen.findByText('Enterprise A')).toBeTruthy();
    expect(screen.getByText('MEMBER')).toBeTruthy();
  });
});
