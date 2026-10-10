import { SUCCESS_CODE } from '@/constants/codes.constants';

/**
 * 菜单加载状态。
 *
 * 之前 menuTree 为空数组同时意味着「还没加载」「加载失败」「没有权限」三件事，
 * 调用方无法区分，只能一律当成无权限处理，于是接口偶发失败或仍在加载时
 * 用户会被判 403 或看到空的导航栏。这里把结论独立出来：
 * - IDLE      未加载
 * - LOADING   加载中
 * - NO_USER   未就绪：本地拿不到用户信息，无从判定权限
 * - READY     已加载，且服务端返回了菜单
 * - EMPTY     已加载，服务端返回空列表 —— 这才是真正的「无权限」
 * - FAILED    加载失败，权限未知
 */
export type MenuStatus =
  | 'IDLE'
  | 'LOADING'
  | 'NO_USER'
  | 'READY'
  | 'EMPTY'
  | 'FAILED';

export interface MenuStatusFlags {
  /** 已有服务端结论（READY 或 EMPTY）。EMPTY 也是结论：服务端确认无任何菜单权限 */
  settled: boolean;
  /** 服务端确认无任何菜单权限 */
  empty: boolean;
  /** 权限未知：未加载、加载中、用户信息未就绪 */
  pending: boolean;
  /** 加载失败，权限未知 */
  failed: boolean;
}

/**
 * 根据菜单接口响应推断状态。
 *
 * 关键点是业务失败（code 非成功）必须落到 FAILED 而不是 EMPTY：
 * 只有服务端明确返回了空列表，才说明这个账号没有权限。
 */
export const resolveMenuStatusFromResponse = (response: {
  code?: string;
  data?: unknown[] | null;
}): MenuStatus => {
  if (!response || response.code !== SUCCESS_CODE) {
    return 'FAILED';
  }
  return response.data && response.data.length > 0 ? 'READY' : 'EMPTY';
};

export const describeMenuStatus = (status: MenuStatus): MenuStatusFlags => ({
  settled: status === 'READY' || status === 'EMPTY',
  empty: status === 'EMPTY',
  pending: status === 'IDLE' || status === 'LOADING' || status === 'NO_USER',
  failed: status === 'FAILED',
});
