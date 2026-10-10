/**
 * 菜单加载状态的单元测试。
 *
 * 回归目标：菜单接口失败或用户信息未就绪时，不能再被当成「无权限」。
 * 之前三者都表现为 menuTree === []，导致误判 403 或空的导航栏。
 */
import { describe, expect, it } from 'vitest';
import {
  describeMenuStatus,
  resolveMenuStatusFromResponse,
  type MenuStatus,
} from '../menuStatus';

describe('resolveMenuStatusFromResponse', () => {
  it('returns READY when the response carries menus', () => {
    expect(
      resolveMenuStatusFromResponse({ code: '0000', data: [{ id: 1 }] }),
    ).toBe('READY');
  });

  it('returns EMPTY only when the server explicitly sends an empty list', () => {
    expect(resolveMenuStatusFromResponse({ code: '0000', data: [] })).toBe(
      'EMPTY',
    );
  });

  it('treats a null data field as EMPTY', () => {
    expect(resolveMenuStatusFromResponse({ code: '0000', data: null })).toBe(
      'EMPTY',
    );
  });

  it('returns FAILED for a business failure instead of degrading to EMPTY', () => {
    expect(resolveMenuStatusFromResponse({ code: '5000', data: [] })).toBe(
      'FAILED',
    );
  });

  it('returns FAILED for an empty response', () => {
    expect(resolveMenuStatusFromResponse({})).toBe('FAILED');
  });
});

describe('describeMenuStatus', () => {
  const all: MenuStatus[] = [
    'IDLE',
    'LOADING',
    'NO_USER',
    'READY',
    'EMPTY',
    'FAILED',
  ];

  it('treats only READY and EMPTY as settled by the server', () => {
    const settled = all.filter((status) => describeMenuStatus(status).settled);
    expect(settled).toEqual(['READY', 'EMPTY']);
  });

  it('treats only EMPTY as no permission', () => {
    const empty = all.filter((status) => describeMenuStatus(status).empty);
    expect(empty).toEqual(['EMPTY']);
  });

  it('treats IDLE, LOADING and NO_USER as unknown permission', () => {
    const pending = all.filter((status) => describeMenuStatus(status).pending);
    expect(pending).toEqual(['IDLE', 'LOADING', 'NO_USER']);
  });

  it('treats FAILED as a load failure only, not as no permission or unknown', () => {
    const flags = describeMenuStatus('FAILED');
    expect(flags.failed).toBe(true);
    expect(flags.empty).toBe(false);
    expect(flags.pending).toBe(false);
    expect(flags.settled).toBe(false);
  });

  it('keeps pending and settled mutually exclusive and covers every status', () => {
    for (const status of all) {
      const flags = describeMenuStatus(status);
      expect(flags.pending && flags.settled).toBe(false);
    }
    const decisive = all.filter((status) => {
      const flags = describeMenuStatus(status);
      return flags.settled || flags.failed;
    });
    expect(decisive).toEqual(['READY', 'EMPTY', 'FAILED']);
  });
});
