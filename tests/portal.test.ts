import { describe, expect, it, vi } from 'vitest';
import { resolvePortalSlug } from '../src/utils/portal';
vi.mock('@/services/i18nRuntime', () => ({ dict: (key: string) => key }));

describe('portal routing', () => {
  it('keeps website and portal backgrounds separate and rejects unsafe CSS URLs', async () => {
    vi.resetModules();
    const portal = await import('../src/utils/portal');
    portal.setWebsiteBackgrounds({ loginBackground: '/logo/official.png' });
    expect(portal.getPageBackgrounds().loginBackground).toBe('/logo/official.png');
    portal.setPortalDefinition({ slug: 'competition', tenantId: 2, title: 'Test', subtitle: '', accent: '#1677ff', enabled: true });
    expect(portal.getPageBackgrounds().loginBackground).toBeUndefined();
    expect(portal.portalBackgroundImage('/logo/test.jpg')).toBe('url("/logo/test.jpg")');
    for (const value of ['https://external/a', '//external/a', '/logo/../a', '/logo/a");color:red', 'javascript:alert(1)'])
      expect(portal.portalBackgroundImage(value)).toBeUndefined();
    vi.resetModules();
  });
  it('clears only this portal session and preserves the official session', async () => {
    vi.resetModules();
    window.history.replaceState({}, '', '/zhichuangbei/login');
    localStorage.setItem('ACCESS_TOKEN', 'official-session');
    localStorage.setItem('portal:zhichuangbei:ACCESS_TOKEN', 'portal-session');
    const { clearTenantSession } = await import('../src/services/tenantSession');
    clearTenantSession();
    expect(localStorage.getItem('ACCESS_TOKEN')).toBe('official-session');
    expect(localStorage.getItem('portal:zhichuangbei:ACCESS_TOKEN')).toBeNull();
    localStorage.removeItem('ACCESS_TOKEN');
    window.history.replaceState({}, '', '/');
    vi.resetModules();
  });
  it('keeps existing platform routes unchanged', () => {
    for (const path of [
      '/',
      '/login',
      '/home',
      '/space/1/develop',
      '/platform/tenants',
      '/my-enterprises',
      '/app/2',
    ])
      expect(resolvePortalSlug(path)).toBeNull();
  });
  it('recognizes dedicated entry paths without partial matches', () => {
    expect(resolvePortalSlug('/zhichuangbei/login')).toBe('zhichuangbei');
    expect(resolvePortalSlug('/school-demo/space/1')).toBe('school-demo');
    expect(resolvePortalSlug('/%2fattack/login')).toBeNull();
    expect(resolvePortalSlug('//example.com')).toBeNull();
  });
  it('namespaces storage and navigation for the current entry', async () => {
    vi.resetModules();
    window.history.replaceState({}, '', '/zhichuangbei/login');
    const portal = await import('../src/utils/portal');
    expect(portal.portalStorageKey('ACCESS_TOKEN')).toBe(
      'portal:zhichuangbei:ACCESS_TOKEN',
    );
    expect(portal.portalPath('/home')).toBe('/zhichuangbei/home');
    expect(portal.portalPath('/zhichuangbei/home')).toBe('/zhichuangbei/home');
    expect(portal.portalPath('https://example.com')).toBe(
      'https://example.com',
    );
    expect(portal.withoutPortalBase('/zhichuangbei/login')).toBe('/login');
    window.history.replaceState({}, '', '/');
    vi.resetModules();
  });
});
