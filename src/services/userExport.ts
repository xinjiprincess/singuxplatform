import { SUCCESS_CODE } from '@/constants/codes.constants';
import type {
  SystemUserListInfo,
  SystemUserListParams,
} from '@/types/interfaces/systemManage';
import { apiSystemUserList } from './systemManage';

export async function getUsersForExport(
  queryFilter: SystemUserListParams['queryFilter'],
) {
  const users: SystemUserListInfo[] = [];
  const ids = new Set<number>();
  let expectedTotal: number | undefined;
  for (let pageNo = 1; pageNo <= 100; pageNo++) {
    const response = await apiSystemUserList({
      pageNo,
      pageSize: 100,
      queryFilter,
    });
    if (response.code !== SUCCESS_CODE) throw new Error('USER_EXPORT_FAILED');
    const { records, total } = response.data;
    if (
      !Number.isSafeInteger(total) ||
      total < 0 ||
      total > 10000 ||
      (expectedTotal !== undefined && total !== expectedTotal)
    )
      throw new Error('USER_EXPORT_CHANGED_OR_TOO_LARGE');
    expectedTotal = total;
    for (const user of records) {
      if (ids.has(user.id)) throw new Error('USER_EXPORT_CHANGED_OR_TOO_LARGE');
      ids.add(user.id);
      users.push(user);
    }
    if (users.length === total) return users;
    if (!records.length || users.length > total)
      throw new Error('USER_EXPORT_FAILED');
  }
  throw new Error('USER_EXPORT_CHANGED_OR_TOO_LARGE');
}
