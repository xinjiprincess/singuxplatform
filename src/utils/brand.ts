/**
 * 品牌 DOM（标签标题、标签图标）的读写。
 *
 * 背景：租户配置会写进 localStorage 并被模型直接用于渲染，于是存在品牌串味风险——
 * 上一个企业的站点名、图标会残留在下一个人的登录页上。
 *
 * 规则（对应方案 §11.1：统一入口永远使用 Singu X 平台品牌）：
 * - 只有拿到本次会话的服务端租户配置，才把企业品牌应用到 DOM；
 * - 身份阶段、配置加载失败、切换企业之后，一律回落到平台品牌。
 */
import type { TenantConfigInfo } from '@/types/interfaces/login';

/**
 * 应用外壳自带的标题。没有企业品牌时恢复成它，
 * 而不是继续显示上一个企业的站点名，也不要写出 "undefined"。
 */
const PLATFORM_TITLE = typeof document === 'undefined' ? '' : document.title;

/**
 * 由本模块管理的图标节点 id。
 * 用固定 id 复用同一个 link 节点：早期实现每次都 append 一个新节点，
 * 切换企业后旧节点仍然留在 head 里，浏览器可能继续使用上一个企业的图标。
 */
const FAVICON_ELEMENT_ID = 'singux-favicon';

/**
 * 设置浏览器标签图标；url 为空时移除此节点，回落到平台默认图标。
 */
export function applyFavicon(url?: string | null): void {
  if (typeof document === 'undefined') {
    return;
  }

  const existing = document.getElementById(
    FAVICON_ELEMENT_ID,
  ) as HTMLLinkElement | null;

  if (!url) {
    existing?.remove();
    return;
  }

  const link = existing ?? document.createElement('link');
  link.id = FAVICON_ELEMENT_ID;
  link.rel = 'shortcut icon';
  link.type = 'image/x-icon';
  link.href = url;

  if (!existing) {
    const head = document.head || document.getElementsByTagName('head')[0];
    head?.appendChild(link);
  }
}

/**
 * 设置标签标题。站点名和描述都为空时回落到平台标题，
 * 避免把标题设成 undefined，或者拼出 - undefined 这种半截值。
 */
export function applyDocumentTitle(
  siteName?: string | null,
  siteDescription?: string | null,
): void {
  if (typeof document === 'undefined') {
    return;
  }

  if (siteName && siteDescription) {
    document.title = `${siteName} - ${siteDescription}`;
    return;
  }

  document.title = siteName || siteDescription || PLATFORM_TITLE;
}

/**
 * 回落到平台品牌：清掉企业图标，恢复外壳标题。
 */
export function applyPlatformBrand(): void {
  applyDocumentTitle();
  applyFavicon(null);
}

/**
 * 应用企业品牌。传入空配置等同于回落到平台品牌，
 * 调用方不需要自己判断该走哪个分支。
 */
export function applyTenantBrand(
  config?: Pick<TenantConfigInfo, 'siteName' | 'siteDescription' | 'faviconUrl'>,
): void {
  if (!config) {
    applyPlatformBrand();
    return;
  }
  applyDocumentTitle(config.siteName, config.siteDescription);
  applyFavicon(config.faviconUrl);
}
