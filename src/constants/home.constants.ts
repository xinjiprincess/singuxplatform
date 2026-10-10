import { dict } from '@/services/i18nRuntime';
import { portalStorageKey } from '@/utils/portal';

export const ACCESS_TOKEN = portalStorageKey('ACCESS_TOKEN');
export const USER_INFO = portalStorageKey('USER_INFO');
// expireDate
export const EXPIRE_DATE = portalStorageKey('EXPIRE_DATE');
export const PHONE = portalStorageKey('PHONE');
export const SPACE_ID = portalStorageKey('SPACE_ID');
export const PATH_URL = portalStorageKey('PATH_URL');

// 租户配置信息
export const TENANT_CONFIG_INFO = portalStorageKey('TENANT_CONFIG_INFO');

// 登录第二步：选择企业。该路由位于工作台布局之外，不加载业务菜单
export const TENANT_SELECT_PATH = '/login/enterprises';

// 应用版本号存储 key
export const APP_VERSION = 'APP_VERSION';

// 推荐聊天主题
export const RECOMMEND_TEXT = [
  dict('PC.Constants.Home.exampleQ1'),
  dict('PC.Constants.Home.exampleQ2'),
  dict('PC.Constants.Home.exampleQ3'),
  dict('PC.Constants.Home.exampleQ4'),
  dict('PC.Constants.Home.exampleQ5'),
];
