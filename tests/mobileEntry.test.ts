import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import { describe, it, expect, vi } from 'vitest';

const source = readFileSync('config/config.ts', 'utf8');
const inline = source.match(/content: `([\s\S]*?)`,/)![1];
function navigate(url: string, mobileEnabled: boolean) {
  const location = new URL(url);
  const replace = vi.fn();
  vm.runInNewContext(inline.replace("${process.env.UMI_ENABLE_MOBILE_APP === 'true'}", String(mobileEnabled)), {
    window: {location:{protocol:location.protocol,host:location.host,href:location.href,hash:location.hash,replace}},
    navigator:{userAgent:'Android Mobile'},
  });
  return replace;
}
describe('mobile deployment routing', () => {
  it('does not redirect phones to an undeployed mobile app by default', () => {
    expect(navigate('https://example.com/login',false)).not.toHaveBeenCalled();
  });
  it('recovers legacy mobile entry links to the web app', () => {
    expect(navigate('https://example.com/m/',false)).toHaveBeenCalledWith('https://example.com/');
  });
  it('only redirects to mobile app when explicitly enabled', () => {
    expect(navigate('https://example.com/login',true)).toHaveBeenCalledWith('https://example.com/m/');
  });
});
