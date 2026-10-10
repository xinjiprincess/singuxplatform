/**
 * 多企业登录分流规则的单元测试。
 *
 * 覆盖 P1 里最容易出错的一处：多企业模式下登录接口只返回 stage，不返回 token。
 * 若分流顺序写反，用户看到的会是「登录失败」，或者验证码登录被送到设置密码页。
 *
 * 测试名统一用英文：scripts/check-hardcoded-i18n.js 会扫描新增行里的中文串，
 * 仓库里 tests/ 下的兄弟测试也全是英文命名。
 */
import { TENANT_SELECTION_REQUIRED } from '@/types/interfaces/login';
import type { ILoginResult } from '@/types/interfaces/login';
import { describe, expect, it } from 'vitest';
import { maskAccount, resolveLoginOutcome } from '../tenantLogin';

const buildResult = (overrides: Partial<ILoginResult>): ILoginResult => ({
  token: null,
  expireDate: null,
  resetPass: null,
  redirect: null,
  ...overrides,
});

describe('resolveLoginOutcome', () => {
  it('returns TENANT_SELECTION when the stage is set, even without a token', () => {
    const outcome = resolveLoginOutcome(
      buildResult({ stage: TENANT_SELECTION_REQUIRED }),
    );

    expect(outcome.kind).toBe('TENANT_SELECTION');
  });

  it('returns TENANT_SELECTION even when resetPass is empty', () => {
    // 验证码登录会先读 resetPass，若分流顺序写反就会被送到设置密码页
    const outcome = resolveLoginOutcome(
      buildResult({ stage: TENANT_SELECTION_REQUIRED, resetPass: null }),
    );

    expect(outcome).toEqual({ kind: 'TENANT_SELECTION' });
  });

  it('returns a usable tenant session token in single-tenant mode', () => {
    const outcome = resolveLoginOutcome(
      buildResult({ token: 'token-1', expireDate: '2026-01-01T00:00:00Z' }),
    );

    expect(outcome).toEqual({
      kind: 'SESSION',
      token: 'token-1',
      expireDate: '2026-01-01T00:00:00Z',
    });
  });

  it('returns INVALID when neither a stage nor a token is present', () => {
    expect(resolveLoginOutcome(buildResult({})).kind).toBe('INVALID');
  });

  it('returns INVALID when the token has no expiry', () => {
    expect(resolveLoginOutcome(buildResult({ token: 'token-1' })).kind).toBe(
      'INVALID',
    );
  });

  it('returns INVALID when the expiry has no token', () => {
    expect(
      resolveLoginOutcome(buildResult({ expireDate: '2026-01-01T00:00:00Z' }))
        .kind,
    ).toBe('INVALID');
  });

  it('returns INVALID for a null or undefined response instead of throwing', () => {
    expect(resolveLoginOutcome(null).kind).toBe('INVALID');
    expect(resolveLoginOutcome(undefined).kind).toBe('INVALID');
  });

  it('does not treat an unknown stage value as tenant selection', () => {
    const outcome = resolveLoginOutcome(
      // @ts-expect-error 模拟服务端返回了前端还不认识的新阶段
      buildResult({ stage: 'SOMETHING_ELSE' }),
    );

    expect(outcome.kind).toBe('INVALID');
  });
});

describe('maskAccount', () => {
  it('keeps the email domain and only the first two characters of the local part', () => {
    expect(maskAccount('admin@singux.local')).toBe('ad***@singux.local');
  });

  it('does not pad a one-character local part', () => {
    expect(maskAccount('a@b.com')).toBe('a***@b.com');
  });

  it('masks a phone number keeping the first three and last two digits', () => {
    expect(maskAccount('13800138000')).toBe('138****00');
  });

  it('does not apply the phone rule to a short numeric account', () => {
    expect(maskAccount('1234')).toBe('12***4');
  });

  it('keeps only the first character of a two-character account', () => {
    expect(maskAccount('ab')).toBe('a*');
  });

  it('returns an empty string for an empty account', () => {
    expect(maskAccount('')).toBe('');
    expect(maskAccount('   ')).toBe('');
  });

  it('never returns the full account', () => {
    const account = 'admin@singux.local';
    expect(maskAccount(account)).not.toBe(account);
  });
});
