import type { MenuItemDto } from '@/types/interfaces/menu';

/** Remove the documentation navigation without changing the server response. */
export function removeDocumentationMenus(items: MenuItemDto[]): MenuItemDto[] {
  return items
    .filter((item) => item.code !== 'documents')
    .map((item) =>
      item.children
        ? { ...item, children: removeDocumentationMenus(item.children) }
        : item,
    );
}
