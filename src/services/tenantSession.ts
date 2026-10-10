import { applyPlatformBrand } from '@/utils/brand';
import { portalPath, portalStorageKey } from '@/utils/portal';
import {
  ACCESS_TOKEN,
  EXPIRE_DATE,
  PATH_URL,
  PHONE,
  SPACE_ID,
  TENANT_CONFIG_INFO,
  USER_INFO,
} from '@/constants/home.constants';
import { STORAGE_KEYS } from '@/constants/theme.constants';

export const TENANT_SESSION_EPOCH = portalStorageKey('SINGUX_TENANT_SESSION_EPOCH');
const initialEpoch =
  typeof window === 'undefined'
    ? null
    : localStorage.getItem(TENANT_SESSION_EPOCH);

export function assertCurrentTenantSession() {
  if (localStorage.getItem(TENANT_SESSION_EPOCH) !== initialEpoch)
    throw new Error('TENANT_SESSION_CHANGED');
}

/**
 * 清除当前企业会话的全部痕迹：令牌、用户信息、缓存、品牌。
 *
 * 两个调用时机都要求它连令牌一起清掉：
 * 1. 切换/选择企业前（applyTenantSession），随后会写入新企业的令牌；
 * 2. 进入身份阶段前（重新登录、选择企业页）。
 *
 * 第 2 点尤其关键：多企业开关打开时后端优先采用 Authorization 头而不是 ticket
 * Cookie，浏览器里残留的上一个企业令牌会让身份阶段的请求（/api/me/tenants）
 * 带着旧企业身份发出，表现为列表错乱，或者直接被判成未登录。
 */
export function clearTenantSession() {
  for (const key of new Set([
    ACCESS_TOKEN,
    USER_INFO,
    TENANT_CONFIG_INFO,
    SPACE_ID,
    PATH_URL,
    PHONE,
    EXPIRE_DATE,
    TENANT_SESSION_EPOCH,
    ...Object.values(STORAGE_KEYS),
  ])) {
    localStorage.removeItem(key);
  }
  sessionStorage.removeItem(portalStorageKey('userLoginStatus'));
  // 清掉上一个企业的品牌痕迹。localStorage 清空只影响后续渲染，
  // 此时标签页上还挂着上一个企业的站点名和图标（选择企业页正是身份阶段，
  // 不该出现任何一个企业的品牌），必须显式回落到平台品牌。
  applyPlatformBrand();
}

export function applyTenantSession(session: {
  token: string;
  tenantId: number;
  expiresIn: number;
}) {
  clearTenantSession();
  localStorage.setItem(ACCESS_TOKEN, session.token);
  localStorage.setItem(
    EXPIRE_DATE,
    new Date(Date.now() + session.expiresIn * 1000).toISOString(),
  );
  localStorage.setItem(
    TENANT_SESSION_EPOCH,
    `${session.tenantId}:${crypto.randomUUID()}`,
  );
  window.location.replace(portalPath('/home'));
}
export function watchTenantSession() {
  const listener = (event: StorageEvent) => {
    if (
      event.key === TENANT_SESSION_EPOCH &&
      event.oldValue !== event.newValue
    ) {
      sessionStorage.removeItem(portalStorageKey('userLoginStatus'));
      window.location.replace(portalPath('/home'));
    }
  };
  window.addEventListener('storage', listener);
  return () => window.removeEventListener('storage', listener);
}
