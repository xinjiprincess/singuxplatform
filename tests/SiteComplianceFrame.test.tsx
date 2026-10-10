import React from 'react';
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import SiteComplianceFrame from '../src/components/SiteComplianceFrame';

vi.mock('../src/components/SiteComplianceFrame/index.less', () => ({
  default: { frame: 'frame', content: 'content', footer: 'footer' },
}));

afterEach(cleanup);

describe('site compliance footer', () => {
  it('keeps page content and separates ICP and police lookup links', () => {
    render(<SiteComplianceFrame><main>Page content</main></SiteComplianceFrame>);
    expect(screen.getByRole('main')).toHaveTextContent('Page content');
    expect(screen.getByRole('contentinfo')).toHaveAccessibleName('网站备案信息');
    expect(screen.getByRole('link', { name: '蜀ICP备2026030409号' })).toHaveAttribute('href', 'https://beian.miit.gov.cn/');
    expect(screen.getByRole('link', { name: '公安备案查询' })).toHaveAttribute('href', 'https://beian.mps.gov.cn/#/query/webSearch');
    for (const link of screen.getAllByRole('link')) {
      expect(link).toHaveAttribute('target', '_blank');
      expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    }
    expect(screen.queryByText(/powered by|nuwax|女娲/i)).toBeNull();
  });
});
