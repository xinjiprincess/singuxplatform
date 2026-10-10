import type { RoleEnum, UserStatus } from '@/types/enums/common';
import type { SendCodeEnum } from '@/types/enums/login';

// 账号密码登录请求参数
export type LoginFieldType = {
  phoneOrEmail: string;
  areaCode: string;
  password?: string;
  captchaVerifyParam?: string;
};

// 登录阶段：身份已验证，但尚未选择企业
export const TENANT_SELECTION_REQUIRED = 'TENANT_SELECTION_REQUIRED';

export type LoginEntryMode = 'select' | 'invitation' | 'platform';

// 登录响应数据
// 单租户模式（多企业开关关闭）直接在响应体返回 token；
// 多企业模式（开关打开）token 只写入 HttpOnly ticket Cookie，响应体返回 stage，
// 前端拿不到也不需要拿 token，必须先去选择企业。
export interface ILoginResult {
  token: string | null;
  expireDate: string | null;
  resetPass: number | null;
  redirect: string | null;
  // 多企业模式下为 TENANT_SELECTION_REQUIRED
  stage?: typeof TENANT_SELECTION_REQUIRED | null;
  // 身份会话过期时间，仅选择企业阶段返回
  identityExpiresAt?: string | null;
  // 选择企业阶段的入口方式
  entryMode?: LoginEntryMode | null;
}

// 是否进入「先选择企业」阶段
export const isTenantSelectionRequired = (
  result: ILoginResult | null | undefined,
): boolean => result?.stage === TENANT_SELECTION_REQUIRED;

// 发送验证码
export interface SendCode {
  type: SendCodeEnum;
  captchaVerifyParam?: string;
  phone?: string;
  email?: string;
  // 验证票据
  ticket?: string;
}

// 验证码登录请求参数
export interface CodeLogin {
  phone: string;
  code: string;
}

// 首次登录设置密码
export interface SetPasswordParams {
  password: string;
}

// 设置密码
export type SetPasswordFieldType = {
  password: string;
  confirmPassword: string;
};

// 绑定邮箱输入参数
export interface BindEmailParams {
  email?: string;
  phone?: string;
  code: string;
}

// 更新用户信息
export interface UserUpdateParams {
  userName?: string;
  nickName?: string;
  avatar?: string;
  lang?: string;
}

// 重置密码
export interface ResetPasswordParams {
  newPassword: string;
  code: string;
}

// 重置密码form
export interface ResetPasswordForm extends ResetPasswordParams {
  password: string;
}

export interface UserInfo {
  id: number;
  tenantId: number;
  userName: string;
  nickName: string;
  avatar: string;
  password: string;
  // 判断用户是否设置过密码，如果未设置过，需要弹出密码设置框让用户设置密码
  resetPass: number;
  // 用户状态
  status: UserStatus;
  role: RoleEnum;
  email: string;
  phone: string;
  lastLoginTime: string;
  created: string;
  modified: string;
  lang?: string;
}

// 滑动验证码弹窗类型
export type ModalSliderCaptchaType = {
  open: boolean;
  onCancel: (open: boolean) => void;
  onSuccess: () => void;
};

// 租户配置信息
export interface TenantConfigInfo {
  /** 是否开启沙箱功能（通用型智能体、技能管理） */
  enabledSandbox?: boolean;
  /** 是否支持自定义域名绑定 */
  supportCustomDomain?: boolean;
  workflowPublishAudit?: number;
  /*站点名称 */
  siteName: string;

  /* */
  siteUrl: string;

  /*站点描述 */
  siteDescription: string;

  /*站点LOGO，为空使用现有默认的 */
  siteLogo: string;

  /* */
  faviconUrl: string;

  /*登录页banner */
  loginBanner: string;

  /*登录页banner文案 */
  loginBannerText: string;

  /*广场Banner地址，为空使用现有默认的 */
  squareBanner: string;

  /*广场Banner文案标题 */
  squareBannerText: string;

  /*广场Banner文案副标题 */
  squareBannerSubText: string;

  /*广场Banner链接，如果链接不为空，点击跳转 */
  squareBannerLinkUrl: string;

  /*开启注册, 0 关闭；1 开启，如果为0，前端不展示注册入口 */
  openRegister: number;

  /*默认会话模型 */
  defaultChatModelId: number;

  /*默认嵌入模型 */
  defaultEmbedModelId: number;

  /*默认知识库模型 */
  defaultKnowledgeModelId: number;

  /*默认站点Agent */
  defaultAgentId: number;

  /*默认通用型智能体Agent */
  defaultTaskAgentId?: number;

  /*首页会话框下的推荐问题 */
  homeRecommendQuestions: Record<string, unknown>[];

  /*官方智能体配置 */
  officialAgentIds: Record<string, unknown>[];

  /*官方用户名 */
  officialUserName: string;

  /*站点域名 */
  domainNames: Record<string, unknown>[];

  /* */
  casClientHostUrl: string;

  /* */
  casValidateUrl: string;

  /* */
  casLoginUrl: string;

  /* */
  authType: number;

  /* */
  agentPublishAudit: number;

  /* */
  pluginPublishAudit: number;

  /* */
  userWhiteList: Record<string, unknown>[];

  /* */
  codeSafeCheckPrompt: string;

  /* */
  openCodeSafeCheck: number;

  /* */
  globalSystemPrompt: string;

  /* */
  smtpHost: string;

  /* */
  smtpPort: number;

  /* */
  smtpUsername: string;

  /* */
  smtpPassword: string;

  /* */
  smsAccessKeyId: string;

  /* */
  smsAccessKeySecret: string;

  /* */
  smsSignName: string;

  /* */
  smsTemplateCode: string;

  /* */
  authExpire: number;

  /** 主题模板配置（JSON字符串） */
  templateConfig?: string;

  /* */
  openCaptcha: number;

  /* */
  captchaAccessKeyId: string;

  /* */
  captchaAccessKeySecret: string;

  /* */
  captchaPrefix: string;

  /* */
  captchaSceneId: string;

  /*登录页文案 */
  loginPageText?: string;

  /*登录页副文案 */
  loginPageSubText?: string;

  /*最大上传文件大小，例如 100MB */
  maxFileSize?: string;

  /*CAS响应用户属性配置，格式为JSON，如：{"uid":"cas:user","userName":"cas:edu_userName","nickName":"cas:edu_name","phone":"cas:edu_phone","email":"cas:edu_email"} */
  casUserAttributesConfig?: string;

  /* */
  skillPublishAudit?: number;

  /* */
  pageFooterText?: string;

  /* */
  allowAgentTempChat?: number;

  /* */
  allowAgentApi?: number;

  /* */
  allowMcpExport?: number;

  /* */
  version?: string;

  /* */
  homeSlogan?: string;

  /*默认编码模型 */
  defaultCodingModelId?: number;

  /*默认视觉模型 */
  defaultVisualModelId?: number;

  /* */
  mpAppId?: string;

  /* */
  mpAppSecret?: string;

  /* */
  sandboxConfig?: string;

  /* */
  userComputerDefaultSkillIds?: string;

  /* */
  officialPluginIds?: string;

  /* */
  officialWorkflowIds?: string;

  /* */
  officialSkillIds?: string;

  /*收入分成比例 */
  revenueRatio?: Record<string, unknown>;

  /*支付网关地址 */
  paymentGateway?: string;

  /*是否开启订阅模式 */
  enableSubscription?: number;

  /*积分兑换比例，比如 1000标识1块钱可以兑换1000积分 */
  creditExchangeRate?: number;

  /*积分兑换说明 */
  creditExchangeDesc?: string;

  /*是否开启注册积分赠送 */
  enableGiftCredit?: number;

  /*注册赠送积分数 */
  giftCreditAmount?: number;

  /*注册赠送积分有效期（天） */
  giftCreditExpire?: number;

  /*是否开启每日登录赠送积分 */
  enableDailyGiftCredit?: number;

  /*每日登录赠送积分数 */
  dailyGiftCreditAmount?: number;

  /* */
  commercialEdition?: boolean;

  /** 模型 OpenAPI 调用基础地址（拼接模型标识 model 字段） */
  baseModelApiUrl?: string;
}

// 设置用户账号信息
export interface SetUserAccountInfo {
  userName: string;
  nickName: string;
}
