import { describe, expect, it } from 'vitest';
import { removeDocumentationMenus } from '../src/utils/visibleMenus';
import type { MenuItemDto } from '../src/types/interfaces/menu';

describe('documentation navigation', () => {
  it('removes documentation at every level without mutating input', () => {
    const menus = [
      { code: 'documents' },
      { code: 'group', children: [{ code: 'documents' }, { code: 'knowledge' }] },
      { code: 'notification' },
    ] as MenuItemDto[];
    expect(removeDocumentationMenus(menus)).toEqual([
      { code: 'group', children: [{ code: 'knowledge' }] },
      { code: 'notification' },
    ]);
    expect(menus[1].children).toHaveLength(2);
    expect(menus).toHaveLength(3);
  });

  it('preserves document processing features and empty input', () => {
    expect(removeDocumentationMenus([])).toEqual([]);
    const menus = [{ code: 'document_extract' }] as MenuItemDto[];
    expect(removeDocumentationMenus(menus)).toEqual(menus);
  });
});
