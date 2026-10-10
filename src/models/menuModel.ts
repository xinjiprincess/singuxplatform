/**
 * 动态菜单权限管理 Model
 * @description 管理用户的菜单树数据和功能权限，提供权限检查方法
 */
import { apiQueryMenus } from '@/services/menuService';
import { UserService } from '@/services/userService';
import type { MenuItemDto } from '@/types/interfaces/menu';
import { removeDocumentationMenus } from '@/utils/visibleMenus';
import { portalSlug } from '@/utils/portal';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useModel } from 'umi';

import { OTHER_MENU_CODES } from '@/constants/menus.constants';
import { MenuEnabledEnum } from '@/pages/SystemManagement/MenuPermission/types/menu-manage';
import {
  describeMenuStatus,
  resolveMenuStatusFromResponse,
  type MenuStatus,
} from '@/utils/menuStatus';
import {
  extractAllMenuCodes,
  extractAllPermissions,
  isRoutePathHidden,
} from '@/utils/permission';

export type { MenuStatus };

/**
 * 菜单权限模型
 */
export default function useMenuModel() {
  // 获取租户配置信息
  const { tenantConfigInfo } = useModel('tenantConfigInfo');
  // 缓存最原始的菜单数据，用作响应式过滤的数据源
  const rawMenusRef = useRef<MenuItemDto[]>([]);

  // 菜单树数据
  const [menuTree, setMenuTree] = useState<MenuItemDto[]>([]);
  // 权限码集合（用于快速查找）
  const [permissionSet, setPermissionSet] = useState<Set<string>>(new Set([]));
  // 权限码集合（用于快速查找）
  const [permissionsMap, setPermissionsMap] = useState<Map<string, string[]>>(
    new Map(),
  );
  // 菜单码集合（用于检查菜单访问权限）
  const [menuCodeSet, setMenuCodeSet] = useState<Set<string>>(new Set([]));

  // 加载状态
  const [loading, setLoading] = useState<boolean>(false);
  // 菜单加载状态，用于区分「无权限」和「还没结论」
  const [menuStatus, setMenuStatus] = useState<MenuStatus>('IDLE');

  // 标记是否已从 initialState 初始化
  const initializedRef = useRef<boolean>(false);

  // 获取全局初始状态（包含预加载的菜单数据）
  const { initialState } = useModel('@@initialState');

  /**
   * 处理菜单数据：设置菜单树、权限码、菜单码
   */
  const processMenuData = useCallback(
    (menus: MenuItemDto[]) => {
      rawMenusRef.current = menus;

      const isHiddenMenu = (menu: MenuItemDto): boolean => {
        if (!menu.path) return false;
        const normalizedPath = menu.path.split('?')[0];
        if (portalSlug && (normalizedPath.startsWith('/platform/') || normalizedPath === '/my-enterprises')) return true;
        return isRoutePathHidden(normalizedPath, tenantConfigInfo);
      };

      const filterItems = (items: MenuItemDto[]): MenuItemDto[] => {
        return items
          .filter((item) => !isHiddenMenu(item))
          .map((item) => {
            if (item.children?.length) {
              return {
                ...item,
                children: filterItems(item.children),
              };
            }
            return item;
          })
          .filter((item) => {
            // 没有 path 的菜单不需要隐藏 【比如 通知】
            if (!item.path) return true;

            // 如果一个菜单项本应有子菜单（即 children 被声明且过滤前长度大于 0），
            // 但经过过滤后其 children 列表变成了空数组，说明其所有子菜单均被隐藏，
            // 此时如果它自身没有独立的有效可访问路由路径（或者属于结构性导航组，如以 '#' 或空串等为 path 的节点），
            // 则该空壳父菜单节点也应当一并予以隐藏，避免展示空白下拉。
            if (item.children && item.children.length === 0) {
              const hasValidPath =
                item.path && item.path !== '#' && item.path !== '';
              return hasValidPath;
            }
            return true;
          });
      };

      const filteredMenus = filterItems(removeDocumentationMenus(menus));

      setMenuTree(filteredMenus);

      // 提取所有权限码（从 Map 中提取所有值并打平）
      const permissionsMapData: Map<string, string[]> =
        extractAllPermissions(filteredMenus);
      const permissions: string[] = [];
      permissionsMapData.forEach((codes) => {
        permissions.push(...codes);
      });
      setPermissionSet(new Set(permissions));
      setPermissionsMap(permissionsMapData);

      // 提取所有菜单码
      const menuCodes = extractAllMenuCodes(filteredMenus);
      setMenuCodeSet(new Set(menuCodes));
    },
    [tenantConfigInfo?.enableSubscription],
  );

  // 当租户订阅开关状态变化时，重新基于最原始的菜单树数据源进行响应式过滤与权限重算
  useEffect(() => {
    if (rawMenusRef.current.length > 0) {
      processMenuData(rawMenusRef.current);
    }
  }, [tenantConfigInfo?.enableSubscription, processMenuData]);

  /**
   * 从 initialState 初始化菜单数据
   * 在 model 首次使用时自动执行
   *
   * 这里必须使用 getInitialState 给出的结论，而不是用 menuData.length 反推：
   * 空数组既可能是「服务端确认无权限」，也可能是「用户信息没拿到」或「接口失败」，
   * 反推会把后两者误判成无权限。
   */
  useEffect(() => {
    if (initializedRef.current) return;
    const status = initialState?.menuStatus;
    if (!status || status === 'IDLE' || status === 'LOADING') return;

    if (status === 'NO_USER' || status === 'FAILED') {
      // 尚未有结论，保留状态等待 loadMenus 重试
      setMenuStatus(status);
      return;
    }

    initializedRef.current = true;
    processMenuData(initialState?.menuData || []);
    setMenuStatus(status);
  }, [
    initialState?.menuData,
    initialState?.menuStatus,
    processMenuData,
  ]);

  /**
   * 加载菜单数据
   * @param force 是否强制重新加载（用于登录成功后刷新菜单）
   */
  const loadMenus = useCallback(
    async (force: boolean = false) => {
      // 已经拿到过服务端结论（有菜单或无权限）且不是强制刷新时，不重复请求；
      // 失败和未就绪允许重试，否则用户永远停在未知状态。
      if (
        !force &&
        initializedRef.current &&
        (menuStatus === 'READY' || menuStatus === 'EMPTY')
      ) {
        return;
      }

      setLoading(true);
      setMenuStatus('LOADING');
      try {
        const userInfo = UserService.getUserInfoFromStorage();
        if (!userInfo?.id) {
          // 用户信息还没就绪，不能据此判定无权限
          setMenuStatus('NO_USER');
          return;
        }
        const res = await apiQueryMenus();
        const status = resolveMenuStatusFromResponse(res);
        if (status === 'FAILED') {
          // 业务失败同样是「权限未知」，不能当成无权限
          setMenuStatus('FAILED');
          return;
        }
        initializedRef.current = true;
        // READY 也要把菜单写进去；EMPTY 时写入空数组，清掉上一个账号残留的权限
        processMenuData(res.data || []);
        setMenuStatus(status);
      } catch (error) {
        console.error('Failed to load menu data:', error);
        setMenuStatus('FAILED');
      } finally {
        setLoading(false);
      }
    },
    [menuStatus, processMenuData],
  );

  /**
   * 需要单独分离的菜单 code 列表
   * documents：文档
   * notification：通知
   * my_computer：我的电脑
   */

  /**
   * 一级菜单列表（排除 documents、notification、my_computer、more_page）
   */
  const firstLevelMenus = useMemo(
    () =>
      menuTree?.filter(
        (menu: MenuItemDto) =>
          menu.status === MenuEnabledEnum.Enabled &&
          !OTHER_MENU_CODES.includes(menu.code || ''),
      ),
    [menuTree],
  );

  /**
   * 其他菜单列表（只包含 documents、notification、my_computer、more_page）
   */
  const otherMenus = useMemo(() => {
    const menu = menuTree?.filter(
      (menu: MenuItemDto) =>
        menu.status === MenuEnabledEnum.Enabled &&
        OTHER_MENU_CODES.includes(menu.code || ''),
    );
    return [...menu];
  }, [menuTree]);

  /**
   * 根据父级菜单 code 获取其子菜单列表（递归查找）
   * @description 不再只在一级菜单中查找，而是递归整个菜单树
   */
  const getSecondLevelMenus = useCallback(
    (parentCode: string): MenuItemDto[] => {
      if (!menuTree?.length) return [];

      const findParent = (items: MenuItemDto[]): MenuItemDto | undefined => {
        for (const item of items) {
          if (item.code === parentCode) {
            return item;
          }
          if (item.children?.length) {
            const found = findParent(item.children);
            if (found) {
              return found;
            }
          }
        }
        return undefined;
      };

      const parent = findParent(menuTree);
      return (
        parent?.children?.filter(
          (menu: MenuItemDto) => menu.status === MenuEnabledEnum.Enabled,
        ) || []
      );
    },
    [menuTree],
  );

  /**
   * 根据路径查找对应的菜单项
   */
  const findMenuByPath = useCallback(
    (path: string): MenuItemDto | undefined => {
      const traverse = (items: MenuItemDto[]): MenuItemDto | undefined => {
        for (const item of items) {
          if (item.path === path) {
            return item;
          }
          if (item.children?.length) {
            const found = traverse(item.children);
            if (found) return found;
          }
        }
        return undefined;
      };
      return traverse(menuTree);
    },
    [menuTree],
  );

  /**
   * 检查是否有某个功能权限
   */
  const hasPermission = useCallback(
    (code: string): boolean => {
      return permissionSet.has(code);
    },
    [permissionSet],
  );

  /**
   * 检查是否有某个功能权限
   */
  const hasPermissionByMenuCode = useCallback(
    (menuCode: string, permissionCode: string): boolean => {
      return permissionsMap.get(menuCode)?.includes(permissionCode) || false;
    },
    [permissionsMap],
  );

  /**
   * 检查是否有多个权限中的任意一个
   */
  const hasAnyPermission = useCallback(
    (codes: string[]): boolean => {
      return codes.some((code) => permissionSet.has(code));
    },
    [permissionSet],
  );

  /**
   * 检查是否有所有指定权限
   */
  const hasAllPermissions = useCallback(
    (codes: string[]): boolean => {
      return codes.every((code) => permissionSet.has(code));
    },
    [permissionSet],
  );

  /**
   * 检查是否有某个菜单的访问权限
   */
  const hasMenuAccess = useCallback(
    (menuCode: string): boolean => {
      return menuCodeSet.has(menuCode);
    },
    [menuCodeSet],
  );

  /**
   * 获取页面对应的功能权限列表
   */
  const getPagePermissions = useCallback(
    (path: string): string[] => {
      const menu = findMenuByPath(path);
      return menu?.resourceTree?.map((r) => r.code || '') || [];
    },
    [findMenuByPath],
  );

  /**
   * 清除菜单信息
   * 用于退出登录时清除菜单数据，确保下次登录会重新加载
   */
  const clearMenuInfo = useCallback(() => {
    setMenuTree([]);
    setPermissionSet(new Set([]));
    setPermissionsMap(new Map());
    setMenuCodeSet(new Set([]));
    // 重置初始化标记，确保下次登录会重新加载菜单
    initializedRef.current = false;
    // 回到「未加载」，避免把上一个账号的权限结论留给下一个账号
    setMenuStatus('IDLE');
  }, []);

  /**
   * 状态的派生布尔值。调用方按语义取用，避免各自去比较 menuStatus 字符串：
   * - menuSettled 已有服务端结论（READY 或 EMPTY），EMPTY 也是结论
   * - menuEmpty   服务端确认该账号没有任何菜单权限
   * - menuPending 还没有结论：未加载 / 加载中 / 用户信息未就绪，
   *               此时既不能判定有权限，也不能判定无权限
   * - menuFailed  加载失败，权限未知
   */
  const {
    settled: menuSettled,
    empty: menuEmpty,
    pending: menuPending,
    failed: menuFailed,
  } = describeMenuStatus(menuStatus);

  return {
    // 状态
    menuTree,
    loading,
    menuStatus,
    menuSettled,
    menuEmpty,
    menuPending,
    menuFailed,
    // 菜单数据获取
    loadMenus,
    firstLevelMenus,
    otherMenus,
    getSecondLevelMenus,
    findMenuByPath,
    clearMenuInfo,
    // 权限检查
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    hasMenuAccess,
    getPagePermissions,
    permissionSet,
    permissionsMap,
    hasPermissionByMenuCode,
  };
}
