export interface PortalDefinition {
  slug: string;
  tenantId: number;
  title: string;
  subtitle: string;
  logo?: string;
  favicon?: string;
  loginBackground?: string;
  workspaceBackground?: string;
  accent: string;
  enabled: boolean;
  startsAt?: string;
  endsAt?: string;
}
export interface WebsiteBackgrounds {
  loginBackground?: string;
  workspaceBackground?: string;
}
let websiteBackgrounds: WebsiteBackgrounds = {};
export const setWebsiteBackgrounds = (value: WebsiteBackgrounds) => { websiteBackgrounds = value; };
export const getPageBackgrounds = (): WebsiteBackgrounds => definition || websiteBackgrounds;

export const portalRootRoutes = [
  '',
  'login',
  'verify-code',
  'set-password',
  'chat-temp',
  'home',
  'platform',
  'my-enterprises',
  'open-iframe-page',
  'my-computer-manage',
  'agent',
  'space',
  'square',
  'history-conversation',
  'more-page',
  'system',
  'ecosystem',
  'app',
  'license-expired',
  'examples',
  'api',
  'assets',
  'logo',
  'website-backgrounds',
  'm',
];
const rootRoutes = new Set(portalRootRoutes);

export function resolvePortalSlug(pathname: string): string | null {
  const first = pathname.split('/')[1] || '';
  return !rootRoutes.has(first) && /^[a-z][a-z0-9-]{2,39}$/.test(first)
    ? first
    : null;
}

export const portalSlug =
  typeof window === 'undefined'
    ? null
    : resolvePortalSlug(window.location.pathname);
export const portalBase = portalSlug ? `/${portalSlug}` : '';
export const portalStorageKey = (key: string) =>
  portalSlug ? `portal:${portalSlug}:${key}` : key;
export const portalPath = (path: string) =>
  path.startsWith('/') &&
  !path.startsWith('//') &&
  path !== portalBase &&
  !path.startsWith(`${portalBase}/`)
    ? `${portalBase}${path}`
    : path;
export const withoutPortalBase = (path: string) =>
  portalBase && (path === portalBase || path.startsWith(`${portalBase}/`))
    ? path.slice(portalBase.length) || '/'
    : path;

let definition: PortalDefinition | null = null;
export const getPortalDefinition = () => definition;
export const portalBackgroundImage = (value?: string) =>
  value && /^\/(?:logo|api\/file)\/[a-zA-Z0-9_./-]+$/.test(value) && !value.includes('..')
    ? `url("${value}")`
    : undefined;
export const setPortalDefinition = (value: PortalDefinition) => {
  definition = value;
};
