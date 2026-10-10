import React, { type PropsWithChildren } from 'react';
import styles from './index.less';

export const ICP_RECORD = '蜀ICP备2026053509号';

const SiteComplianceFrame: React.FC<PropsWithChildren> = ({ children }) => (
  <div className={styles.frame}>
    <div className={styles.content}>{children}</div>
    <footer className={styles.footer} aria-label="网站备案信息">
      <a
        href="https://beian.miit.gov.cn/"
        target="_blank"
        rel="noopener noreferrer"
      >
        {ICP_RECORD}
      </a>
      <a
        href="https://beian.mps.gov.cn/#/query/webSearch"
        target="_blank"
        rel="noopener noreferrer"
      >
        公安备案查询
      </a>
    </footer>
  </div>
);

export default SiteComplianceFrame;
