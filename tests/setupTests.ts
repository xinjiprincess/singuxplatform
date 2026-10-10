import '@testing-library/jest-dom';

// antd 响应式依赖 matchMedia，测试环境补齐
if (typeof window !== 'undefined' && !window.matchMedia) {
  // @ts-expect-error test env polyfill
  window.matchMedia = (query: string) => ({
    media: query,
    matches: false,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  });
}

/**
 * 补回 Web Storage。
 *
 * 当前 vitest 4 + jsdom 27 的组合下，localStorage / sessionStorage 在 window 上
 * 是「属性存在但取值为 undefined」：既不会抛异常，也不可用，于是任何读写存储的
 * 代码都会以 Cannot read properties of undefined (reading 'getItem') 失败，
 * 整个测试文件里的用例会成片倒下（Antv-X6 的 workflowProxyV3 就是如此）。
 *
 * 这里只在缺失时补一份内存实现。已经提供存储的环境不会被覆盖，测试想自己
 * stubGlobal 也不受影响。
 */
const createMemoryStorage = (): Storage => {
  const values = new Map<string, string>();
  return {
    get length() {
      return values.size;
    },
    clear: () => {
      values.clear();
    },
    getItem: (key: string) => (values.has(key) ? values.get(key)! : null),
    key: (index: number) => Array.from(values.keys())[index] ?? null,
    removeItem: (key: string) => {
      values.delete(key);
    },
    setItem: (key: string, value: string) => {
      values.set(key, String(value));
    },
  } as Storage;
};

const installStorage = (target: unknown, name: string): void => {
  if (!target) return;
  try {
    if (typeof (target as Record<string, unknown>)[name] !== 'undefined') return;
    Object.defineProperty(target, name, {
      value: createMemoryStorage(),
      configurable: true,
      writable: true,
    });
  } catch {
    // 目标上已有不可配置的同名属性时保持原状，让用例自己暴露问题
  }
};

for (const name of ['localStorage', 'sessionStorage']) {
  installStorage(globalThis, name);
  if (typeof window !== 'undefined' && (window as unknown) !== globalThis) {
    installStorage(window, name);
  }
}

