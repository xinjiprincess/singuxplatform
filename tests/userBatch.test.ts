import { describe, expect, it } from 'vitest';
import { parseBatchUsers } from '../src/utils/userBatch';
describe('batch roster validation', () => {
  it('keeps leading zero identifiers and strips a UTF-8 BOM', () => {
    expect(
      parseBatchUsers(
        '\uFEFF[{"userName":"cdut001","phone":"0123","password":"abc12345"}]',
      )[0].phone,
    ).toBe('0123');
  });
  it('rejects hidden privilege and tenant assignments', () => {
    expect(() =>
      parseBatchUsers('[{"userName":"u","password":"p","role":"Admin"}]'),
    ).toThrow();
    expect(() =>
      parseBatchUsers('[{"userName":"u","password":"p","tenantId":2}]'),
    ).toThrow();
  });
  it('rejects empty, oversized and non-string input', () => {
    expect(() => parseBatchUsers('[]')).toThrow();
    expect(() =>
      parseBatchUsers(
        JSON.stringify(Array(201).fill({ userName: 'u', password: 'p' })),
      ),
    ).toThrow();
    expect(() =>
      parseBatchUsers('[{"userName":123,"password":"p"}]'),
    ).toThrow();
  });
});
