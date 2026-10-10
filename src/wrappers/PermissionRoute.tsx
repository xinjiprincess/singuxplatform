/**
 * 路由鉴权 Wrapper
 * @description 用于在路由层面控制页面访问权限，无需修改页面组件代码
 */
import NoPermissionPage from '@/pages/403';
import { dict } from '@/services/i18nRuntime';
import { Button, Result } from 'antd';
import React from 'react';
import { Outlet, useModel, useRouteData } from 'umi';

const PermissionRoute: React.FC = () => {
  // 获取当前路由配置信息
  const route = useRouteData().route;
  const { hasPermission, menuPending, menuFailed, loadMenus } =
    useModel('menuModel');

  // 权限还没有结论时既不通过也不拒绝，只显示 loading。
  // 这里不能渲染 403：菜单仍在加载或用户信息未就绪时，无权限是假象。
  if (menuPending) {
    return null;
  }

  // 加载失败同样不等于无权限。给出可重试的提示，避免用户被误导成没有权限。
  if (menuFailed) {
    return (
      <Result
        status="warning"
        title={dict('PC.Pages.Error403.menuLoadFailed')}
        extra={
          <Button type="primary" onClick={() => loadMenus(true)}>
            {dict('PC.Common.Global.refresh')}
          </Button>
        }
      />
    );
  }

  // 获取路由配置中定义的需要的权限
  // 在 routes/index.ts 中配置: { path: '/foo', wrapper: '@/wrappers/PermissionRoute', code: 'user:view' }
  const requiredPermissionCode = (route as any).code;

  if (requiredPermissionCode && !hasPermission(requiredPermissionCode)) {
    // 无权限，直接渲染 403 页面，保持 URL 不变
    // 这样用户可以知道自己访问的是哪个链接被拒绝了
    return <NoPermissionPage />;
  }

  return <Outlet />;
};

export default PermissionRoute;
