import ConditionRender from '@/components/ConditionRender';
import { getPortalDefinition, getPageBackgrounds, portalBackgroundImage } from '@/utils/portal';
import classNames from 'classnames';
import type { PropsWithChildren } from 'react';
import React from 'react';
import { useModel } from 'umi';
import styles from './index.less';
const cx = classNames.bind(styles);

const BasicLayout: React.FC<PropsWithChildren> = ({ children }) => {
  const { tenantConfigInfo, brandReady } = useModel('tenantConfigInfo');

  // 这个外壳服务于身份阶段（登录、验证码、设置密码、选择企业）。
  // 此时还没有选定企业，只能用本次会话从服务端取回的品牌；
  // 本地缓存里那份配置可能属于上一个已登录的企业，画到统一入口上就是品牌串味。
  // 单租户模式下服务端同样会返回本租户的配置，因此等一个请求即可，不会退化成平台默认。
  const brand = brandReady ? tenantConfigInfo : undefined;
  const portal = getPortalDefinition();

  return (
    <div className={cx(styles.container)} style={{ backgroundImage: portalBackgroundImage(getPageBackgrounds().loginBackground) }}>
      <div className={cx(styles['left-box'])}>
        <div className={cx(styles.icon)}>
          <ConditionRender condition={!!(portal?.logo || brand?.siteLogo)}>
            <img
              src={portal?.logo || brand?.siteLogo}
              className={cx(styles.logo)}
              alt=""
            />
          </ConditionRender>
        </div>
        <div className={cx(styles['left-title-box'])}>
          {/*<p>轻松构建部署你</p>*/}
          {/*<p className={cx(styles.title)}>私有的 Agentic AI 解决方案</p>*/}
          {/*<p className={cx(styles['sub-title'])}>*/}
          {/*  提供完善的工作流、插件开发能力，RAG*/}
          {/*  知识库与数据表存储能力，MCP接入以及开放能力*/}
          {/*</p>*/}

          {portal ? (
            <>
              <p className={cx(styles.title)}>{portal.title}</p>
              <p className={cx(styles['sub-title'])}>{portal.subtitle}</p>
            </>
          ) : (
            <>
              <p
                className={cx(styles.title, 'text-ellipsis-2')}
                dangerouslySetInnerHTML={{
                  __html: brand?.loginPageText,
                }}
              />
              <p
                className={cx(styles['sub-title'], 'text-ellipsis-2')}
                dangerouslySetInnerHTML={{
                  __html: brand?.loginPageSubText,
                }}
              />
            </>
          )}
        </div>
      </div>
      <div className={cx(styles['right-box'])}>{children}</div>
    </div>
  );
};

export default BasicLayout;
