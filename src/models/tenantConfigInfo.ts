import { TENANT_CONFIG_INFO } from '@/constants/home.constants';
import { getPortalDefinition, portalStorageKey } from '@/utils/portal';
import { STORAGE_KEYS } from '@/constants/theme.constants';
import { apiTenantConfig } from '@/services/account';
import { unifiedThemeService } from '@/services/unifiedThemeService';
import type { TenantConfigInfo } from '@/types/interfaces/login';
import { applyDocumentTitle, applyPlatformBrand, applyTenantBrand } from '@/utils/brand';
import { initializeWithFallback } from '@/utils/styleInitializer';
import { useCallback, useEffect, useState } from 'react';
import { useRequest } from 'umi';

export default () => {
  const [loadEnd, setLoadEnd] = useState<boolean>(false);
  const [tenantConfigInfo, setTenantConfigInfo] = useState<TenantConfigInfo>();
  /**
   * 租户品牌是否来自本次会话的服务端响应。
   *
   * 从 localStorage 恢复的配置只用于业务字段（限流、认证方式等）的兜底，
   * 不能当成「当前企业的品牌」：那份缓存可能属于上一个已登录的企业。
   * 身份阶段（登录页、选择企业页）据此判断能不能把 Logo 和登录文案画到页面上。
   */
  const [brandReady, setBrandReady] = useState<boolean>(false);

  // 租户配置信息查询接口
  const { run: runTenantConfig, loading } = useRequest(apiTenantConfig, {
    manual: true,
    debounceInterval: 300,
    onSuccess: async (result: TenantConfigInfo) => {
      if (!result) return;
      const portal = getPortalDefinition();
      if (portal) result = { ...result, siteName: portal.title, siteDescription: portal.subtitle,
        siteLogo: portal.logo || '', faviconUrl: portal.favicon || '' };
      setLoadEnd(true);

      // 如果 result 为 null，走错误处理逻辑
      if (!result) {
        console.warn('Tenant configuration interface returned empty data');
        await initializeWithFallback('租户配置为空');
        return;
      }

      setTenantConfigInfo(result);
      localStorage.setItem(TENANT_CONFIG_INFO, JSON.stringify(result));
      if (result.authType !== null) {
        localStorage.setItem(portalStorageKey('AUTH_TYPE'), result.authType.toString());
      }

      // 设置页面标题和图标。只有服务端刚返回的配置才可以当作「当前企业的品牌」，
      // brandReady 就是给身份阶段判断这一点的。
      setBrandReady(true);
      const { siteName, siteDescription, faviconUrl } = result;
      applyTenantBrand({ siteName, siteDescription, faviconUrl });

      // 租户信息保存到localStorage后，重新初始化统一主题服务
      // 让它重新读取包含templateConfig的租户配置
      // console.log('租户配置保存完成，重新初始化统一主题服务');
      // 统一主题服务会自动加载配置，不需要手动调用
      // unifiedThemeService.loadConfiguration();

      const hasUserSwitchTheme = localStorage.getItem(
        STORAGE_KEYS.HAS_USER_SWITCH_THEME,
      );
      const hasLocalThemeConfig = localStorage.getItem(
        STORAGE_KEYS.USER_THEME_CONFIG,
      );
      if (result.templateConfig && !hasUserSwitchTheme) {
        try {
          const templateConfig = JSON.parse(result.templateConfig);
          const currentData = unifiedThemeService.getCurrentData();
          await unifiedThemeService.updateData(
            {
              ...currentData,
              ...templateConfig,
            },
            {
              immediate: true,
            },
          );
          // console.log('已同步租户主题配置（本地无配置）:', templateConfig);
        } catch (error) {
          console.warn('Failed to sync tenant theme color:', error);
        }
      } else if (hasLocalThemeConfig) {
        console.log(
          'Local theme configuration detected, skipping tenant configuration sync',
        );
        unifiedThemeService.updateData(null, { immediate: true });
      }
    },
    onError: async () => {
      setLoadEnd(true);
      // 加载失败时品牌未知。回落到平台品牌，而不是把上一个企业的标题和图标留在标签页上。
      setBrandReady(false);
      applyPlatformBrand();

      // 接口失败时也要初始化 layout navigation CSS 变量，使用兜底方案
      await initializeWithFallback('租户信息接口失败');
    },
  });

  // 从缓存中获取租户配置信息，设置页面title
  const setTitle = () => {
    const tenantConfigInfoString = localStorage.getItem(TENANT_CONFIG_INFO);
    if (!!tenantConfigInfoString) {
      const tenantConfigInfo = JSON.parse(tenantConfigInfoString);
      const { siteName, siteDescription } = tenantConfigInfo;
      applyDocumentTitle(siteName, siteDescription);
    }
  };

  //初始化 从本地缓存里取出租户配置信息
  const initTenantConfigInfo = useCallback(() => {
    const tenantConfigInfoString = localStorage.getItem(TENANT_CONFIG_INFO);
    if (!!tenantConfigInfoString) {
      const tenantConfigInfo = JSON.parse(tenantConfigInfoString);
      setTenantConfigInfo(tenantConfigInfo);
    }
  }, [setTenantConfigInfo]);

  useEffect(() => {
    //初始化
    initTenantConfigInfo();
  }, []);

  return {
    loadEnd,
    loading,
    tenantConfigInfo,
    brandReady,
    runTenantConfig,
    setTitle,
  };
};
