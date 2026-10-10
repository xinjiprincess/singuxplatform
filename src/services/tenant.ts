import {
  THEME_BACKGROUND_CONFIGS,
  THEME_COLOR_CONFIGS,
} from '@/constants/theme.constants';
import { TenantInfo, TenantThemeConfig } from '@/types/tenant';
import { getCurrentTenantProfile } from './tenantPolicy';
import { unifiedThemeService } from './unifiedThemeService';

/**
 * 租户相关API服务
 */

/**
 * 获取租户信息
 * @returns Promise<TenantInfo>
 */
export const getTenantInfo = async (): Promise<TenantInfo> => {
  const profile = await getCurrentTenantProfile();
  // 从 unifiedThemeService 获取实际的主题配置数据
  const currentData = unifiedThemeService.getCurrentData();
  const currentBackground = currentData.backgroundId;
  const currentLayoutStyle = currentData.layoutStyle;
  const currentNavStyle = currentData.navigationStyle;

  // 构建租户主题配置，优先使用实际配置数据
  const tenantThemeConfig: TenantThemeConfig = {
    themeColors: [...THEME_COLOR_CONFIGS],
    backgroundImages: THEME_BACKGROUND_CONFIGS.map((config) => ({
      id: `bg-${config.id}`,
      name: config.name,
      preview: config.url,
      url: config.url,
      isDefault: config.id === 'variant-1',
    })),
    navigationStyles: [
      {
        id: 'style1',
        name: 'Style 1',
        description:
          'Compact mode: 60px width, text hidden, page container has margin and rounded corners',
        isDefault: true,
      },
      {
        id: 'style2',
        name: 'Style 2',
        description:
          'Expanded mode: 73px width, text visible, page container has no margin or rounded corners',
      },
    ],
    // 使用统一主题数据，如果没有则使用默认值
    defaultThemeColor: currentData.primaryColor || '#5147ff',
    defaultBackgroundId: currentBackground || 'variant-1',
    defaultNavigationStyleId:
      currentNavStyle === 'style2' ? 'style2' : 'style1',
    supportDarkMode: true,
    defaultIsDarkMode: currentLayoutStyle === 'dark',
  };

  const tenantInfo: TenantInfo = {
    id: String(profile.tenantId),
    name: profile.name,
    themeConfig: tenantThemeConfig,
  };

  return tenantInfo;
};

/**
 * 获取租户主题配置
 * @returns Promise<TenantThemeConfig>
 */
export const getTenantThemeConfig = async (): Promise<TenantThemeConfig> => {
  const tenantInfo = await getTenantInfo();
  return tenantInfo.themeConfig;
};
