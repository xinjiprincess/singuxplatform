import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('umi', () => ({ request: vi.fn() }));

describe('portal API routing', () => {
  const nativeFetch = window.fetch;
  const nativeOpen = XMLHttpRequest.prototype.open;
  beforeEach(() => {
    vi.resetModules();
    window.history.replaceState({}, '', '/zhichuangbei/login');
  });
  afterEach(() => {
    window.fetch = nativeFetch;
    XMLHttpRequest.prototype.open = nativeOpen;
    window.history.replaceState({}, '', '/');
    vi.resetModules();
  });
  it('adds the routing hint to same-origin fetch but not external requests', async () => {
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ code: '0000', data: { slug: 'zhichuangbei' } }) });
    window.fetch = fetch;
    const { initializePortal } = await import('../src/services/portal');
    await initializePortal();
    await window.fetch('/api/example', { headers: { Authorization: 'Bearer test' } });
    const headers = fetch.mock.calls[1][1].headers as Headers;
    expect(headers.get('X-Singu-Portal')).toBe('zhichuangbei');
    expect(headers.get('Authorization')).toBe('Bearer test');
    await window.fetch('https://example.com/api/example');
    expect(fetch.mock.calls[2][1]).toBeUndefined();
  });
  it('adds the routing hint to XHR uploads only within this origin', async () => {
    window.fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ code: '0000', data: { slug: 'zhichuangbei' } }) });
    XMLHttpRequest.prototype.open = vi.fn();
    const { initializePortal } = await import('../src/services/portal');
    await initializePortal();
    const xhr = { setRequestHeader: vi.fn() };
    XMLHttpRequest.prototype.open.call(xhr as any, 'POST', '/api/file/upload');
    expect(xhr.setRequestHeader).toHaveBeenCalledWith('X-Singu-Portal', 'zhichuangbei');
    xhr.setRequestHeader.mockClear();
    XMLHttpRequest.prototype.open.call(xhr as any, 'POST', 'https://example.com/api/file/upload');
    expect(xhr.setRequestHeader).not.toHaveBeenCalled();
  });
  it('does not initialize an unknown or disabled portal', async () => {
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ code: 'PORTAL_DISABLED' }) });
    window.fetch = fetch;
    const { initializePortal } = await import('../src/services/portal');
    await expect(initializePortal()).rejects.toThrow();
    expect(window.fetch).toBe(fetch);
  });
});
