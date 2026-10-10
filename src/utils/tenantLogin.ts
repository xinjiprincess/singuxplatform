/**
 * 多企业登录流程的纯函数。
 *
 * 这里刻意不依赖 React、umi 和任何服务模块，方便单测直接覆盖分流规则：
 * 登录响应如何解释，是 P1 里最容易出错、且出错后表现为「登录失败」的地方。
 */
import {
  isTenantSelectionRequired,
  type ILoginResult,
} from '@/types/interfaces/login';

/**
 * 登录成功响应的分流结果。
 *
 * 多企业模式下登录接口不再返回 token，而是返回 stage=TENANT_SELECTION_REQUIRED，
 * 令牌只写在 HttpOnly Cookie 里。因此必须「先判阶段、再判令牌」：
 * 反过来会把「身份已验证但尚未选企业」误判成登录失败；
 * 在验证码登录里还会因为 resetPass 为空而被误送到设置密码页。
 */
export type LoginOutcome =
  /** 身份已验证，需要先去选择企业 */
  | { kind: 'TENANT_SELECTION' }
  /** 单租户模式：拿到企业会话令牌，可以直接进入工作台 */
  | { kind: 'SESSION'; token: string; expireDate: string }
  /** 既没有声明阶段也没有令牌，服务端返回不可用 */
  | { kind: 'INVALID' };

export const resolveLoginOutcome = (
  result: ILoginResult | null | undefined,
): LoginOutcome => {
  if (isTenantSelectionRequired(result)) {
    return { kind: 'TENANT_SELECTION' };
  }

  const token = result?.token;
  const expireDate = result?.expireDate;
  if (!token || !expireDate) {
    return { kind: 'INVALID' };
  }

  return { kind: 'SESSION', token, expireDate };
};

/**
 * 账号脱敏：选择企业页只需要足以让用户确认身份的片段，不完整回显账号。
 * 邮箱保留域名（用户靠域名确认是哪个账号），本地部分只留前两位；
 * 纯数字按手机号处理，保留前三位和后两位。
 */
export const maskAccount = (account: string): string => {
  const value = (account || '').trim();
  if (!value) {
    return '';
  }

  const at = value.indexOf('@');
  if (at > 0) {
    const name = value.slice(0, at);
    const domain = value.slice(at + 1);
    return `${name.slice(0, 2)}***@${domain}`;
  }

  if (/^\d{5,}$/.test(value)) {
    return `${value.slice(0, 3)}****${value.slice(-2)}`;
  }

  if (value.length <= 2) {
    return `${value.charAt(0)}*`;
  }
  return `${value.slice(0, 2)}***${value.slice(-1)}`;
};
