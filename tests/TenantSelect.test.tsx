import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
const api = vi.hoisted(() => ({ list: vi.fn(), select: vi.fn(), apply: vi.fn() }));
vi.mock('umi', () => ({ history: { replace: vi.fn() } }));
vi.mock('@/pages/Login/BasicLayout', () => ({ default: ({ children }: React.PropsWithChildren) => <main>{children}</main> }));
vi.mock('@/pages/Login/LoginLangSwitcher', () => ({ default: () => null }));
vi.mock('@/services/account', () => ({ apiLogout: vi.fn() }));
vi.mock('@/services/i18nRuntime', () => ({ dict: (key: string) => key.split('.').pop() }));
vi.mock('@/services/tenantMembership', () => ({ getMyEnterprises: api.list, selectEnterprise: api.select }));
vi.mock('@/services/tenantOnboarding', () => ({ getOnboarding: vi.fn().mockResolvedValue({ enabled: false, profile: null }) }));
vi.mock('@/services/tenantSession', () => ({ applyTenantSession: api.apply }));
vi.mock('@/pages/TenantSelect/Onboarding', () => ({ default: () => null }));
vi.mock('@/pages/TenantSelect/index.less', () => ({ default: {} }));
import TenantSelect from '../src/pages/TenantSelect';
beforeEach(() => {
  localStorage.clear();
  api.list.mockResolvedValue([
    { tenantId: 1, name: 'School A', role: 'OWNER', status: 'ACTIVE', version: 0 },
    { tenantId: 2, name: 'School B', role: 'MEMBER', status: 'ACTIVE', version: 0 },
    { tenantId: 3, name: 'School revoked', role: 'MEMBER', status: 'REVOKED', version: 1 },
  ]);
});
afterEach(() => { cleanup(); vi.clearAllMocks(); });
describe('enterprise selection', () => {
  it('searches by name and hides revoked memberships', async () => {
    render(<TenantSelect />);
    await screen.findByText('School A');
    expect(screen.queryByText('School revoked')).toBeNull();
    fireEvent.change(screen.getByPlaceholderText('searchEnterprise'), { target: { value: 'School B' } });
    expect(screen.queryByText('School A')).toBeNull();
    expect(screen.getByText('School B')).toBeTruthy();
    fireEvent.click(screen.getByRole('radio'));
    api.select.mockResolvedValue({ token: 'tenant-token', tenantId: 2 });
    fireEvent.click(screen.getByRole('button', { name: 'enter' }));
    await waitFor(() => expect(api.select).toHaveBeenCalledWith(2));
  });
  it('clears a hidden selection and shows the no-match state', async () => {
    render(<TenantSelect />);
    await screen.findByText('School A');
    fireEvent.click(screen.getAllByRole('radio')[0]);
    fireEvent.change(screen.getByPlaceholderText('searchEnterprise'), { target: { value: 'missing' } });
    expect(screen.getByText('noSearchResults')).toBeTruthy();
    expect((screen.getByRole('button', { name: 'enter' }) as HTMLButtonElement).disabled).toBe(true);
  });
});
