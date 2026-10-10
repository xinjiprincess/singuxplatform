import { afterEach, describe, expect, it, vi } from 'vitest';
vi.hoisted(() => {
  for (const name of ['localStorage', 'sessionStorage']) {
    const values = new Map<string, string>();
    vi.stubGlobal(name, {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => values.set(key, value),
      removeItem: (key: string) => values.delete(key),
      clear: () => values.clear(),
    });
  }
});
import {
  assertCurrentTenantSession,
  clearTenantSession,
  TENANT_SESSION_EPOCH,
} from '../src/services/tenantSession';
vi.mock('@/constants/home.constants', () => ({
  ACCESS_TOKEN: 'ACCESS_TOKEN',
  EXPIRE_DATE: 'EXPIRE_DATE',
  PATH_URL: 'PATH_URL',
  PHONE: 'PHONE',
  SPACE_ID: 'SPACE_ID',
  TENANT_CONFIG_INFO: 'TENANT_CONFIG_INFO',
  USER_INFO: 'USER_INFO',
}));
vi.mock('@/constants/theme.constants', () => ({
  STORAGE_KEYS: { ACCESS_TOKEN: 'ACCESS_TOKEN', THEME: 'theme' },
}));
afterEach(() => {
  localStorage.clear();
  sessionStorage.clear();
});
describe('enterprise session boundary', () => {
  it('rejects requests and late responses from a previous session generation', () => {
    expect(() => assertCurrentTenantSession()).not.toThrow();
    localStorage.setItem(TENANT_SESSION_EPOCH, 'new-enterprise');
    expect(() => assertCurrentTenantSession()).toThrow(
      'TENANT_SESSION_CHANGED',
    );
  });
  it('clears identity and brand caches but preserves unrelated preferences', () => {
    for (const key of [
      'ACCESS_TOKEN',
      'USER_INFO',
      'TENANT_CONFIG_INFO',
      'SPACE_ID',
      'theme',
      TENANT_SESSION_EPOCH,
    ])
      localStorage.setItem(key, 'old');
    localStorage.setItem('unrelated', 'keep');
    sessionStorage.setItem('userLoginStatus', 'true');
    clearTenantSession();
    expect(localStorage.getItem('ACCESS_TOKEN')).toBeNull();
    expect(localStorage.getItem('TENANT_CONFIG_INFO')).toBeNull();
    // 令牌与代次必须一起清掉：进入身份阶段（重新登录、选择企业页）时，
    // 残留的企业令牌会被后端优先于 ticket Cookie 采用，身份请求就带上了旧企业。
    expect(localStorage.getItem(TENANT_SESSION_EPOCH)).toBeNull();
    expect(sessionStorage.getItem('userLoginStatus')).toBeNull();
    expect(localStorage.getItem('unrelated')).toBe('keep');
  });
});
