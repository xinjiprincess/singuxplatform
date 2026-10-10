import {
  portalSlug,
  setPortalDefinition,
  setWebsiteBackgrounds,
  type WebsiteBackgrounds,
  type PortalDefinition,
} from '@/utils/portal';
import { request } from 'umi';

export async function initializePortal() {
  if (!portalSlug) {
    try { setWebsiteBackgrounds(await loadWebsiteBackgrounds()); } catch { /* Older backends retain default backgrounds. */ }
    return;
  }
  const response = await fetch(`/api/public/portals/${portalSlug}`, {
    cache: 'no-store',
    credentials: 'omit',
  });
  if (!response.ok) throw new Error('专用平台暂不可用');
  const result = await response.json();
  if (result.code !== '0000' || result.data?.slug !== portalSlug)
    throw new Error('专用平台不存在、未启用或已到期');
  setPortalDefinition(result.data);

  // Native fetch covers streaming/upload clients that do not use Umi's request pipeline.
  const originalFetch = window.fetch.bind(window);
  window.fetch = (input, init) => {
    const url = new URL(
      input instanceof Request ? input.url : String(input),
      location.href,
    );
    if (url.origin !== location.origin || !url.pathname.startsWith('/api/'))
      return originalFetch(input, init);
    const headers = new Headers(
      init?.headers ?? (input instanceof Request ? input.headers : undefined),
    );
    headers.set('X-Singu-Portal', portalSlug);
    return originalFetch(input, { ...init, headers });
  };
  // Ant Design Upload uses XHR rather than fetch. Apply the same routing hint.
  const open = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = new Proxy(open, {
    apply(target, xhr: XMLHttpRequest, args) {
      const result = Reflect.apply(target, xhr, args);
      const url = new URL(String(args[1]), location.href);
      if (url.origin === location.origin && url.pathname.startsWith('/api/')) {
        xhr.setRequestHeader('X-Singu-Portal', portalSlug);
      }
      return result;
    },
  });
}

export async function listPortals(): Promise<PortalDefinition[]> {
  const result = await request('/api/platform/portals');
  if (result.code !== '0000') throw new Error(result.message || '读取失败');
  return result.data;
}

export async function loadWebsiteBackgrounds(): Promise<WebsiteBackgrounds> {
  const response = await fetch('/api/public/portals/website-backgrounds', { cache: 'no-store', signal: AbortSignal.timeout(5000) });
  const result = await response.json();
  if (!response.ok || result.code !== '0000') throw new Error('读取官网背景失败');
  return result.data;
}

export async function saveWebsiteBackgrounds(backgrounds: WebsiteBackgrounds, previous: WebsiteBackgrounds, reason: string) {
  const result = await request('/api/platform/website-backgrounds', { method: 'PUT', data: { backgrounds, previous, reason } });
  if (result.code !== '0000') throw new Error(result.message || '保存失败');
  return result.data as WebsiteBackgrounds;
}

export async function savePortal(
  portal: PortalDefinition,
  previous: PortalDefinition | null,
  reason: string,
) {
  const result = await request('/api/platform/portals', {
    method: 'PUT',
    data: { portal, previous, reason },
  });
  if (result.code !== '0000') throw new Error(result.message || '保存失败');
  return result.data as PortalDefinition;
}
