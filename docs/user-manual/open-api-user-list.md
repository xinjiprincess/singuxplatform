# 分页查询用户列表

> 更新：2026-10-04。本章为功能与操作参考，实际菜单取决于服务器授权和环境配置。界面存在不表示生产能力已验收，环境边界以项目操作指南为准。 接口未对线上执行写入验证；服务地址与密钥需替换为实际值。

## 接口信息

**接口地址**:`/api/v1/system/user/list`

**请求方式**:`POST`

**请求数据类型**:`application/json`

**响应数据类型**:`*/*`

**接口描述**:

分页查询用户列表，支持按用户名、昵称、邮箱、手机号、状态、角色等条件过滤

**请求示例**:

```javascript
{
  "pageNo": 1,
  "pageSize": 10,
  "queryFilter": {
    "userName": "测试",
    "status": "Enabled",
    "role": "Admin"
  }
}
```

## 请求参数

**请求头**

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
| --- | --- | --- | --- | --- |
| Authorization | string | 是 | API Key | `Bearer ak-REPLACE_WITH_API_KEY` |

**请求体参数**:

| 参数名称 | 参数说明 | 是否必须 | 数据类型 |
| --- | --- | --- | --- |
| pageNo | 页码 | 是 | integer(int64) |
| pageSize | 每页条数 | 是 | integer(int64) |
| queryFilter | 查询过滤条件 | 否 | UserQueryDto |
|   userName | 用户姓名 | 否 | string |
|   nickName | 昵称 | 否 | string |
|   email | 邮箱 | 否 | string |
|   phone | 手机号码 | 否 | string |
|   status | 用户状态，可用值: Enabled, Disabled | 否 | string |
|   role | 角色，可用值: Admin, User | 否 | string |

**响应参数**:

| 参数名称 | 参数说明 | 类型 | schema |
| --- | --- | --- | --- |
| code | 业务状态码，0000 表示成功，其余失败 | string |  |
| displayCode | 源系统状态码，用于问题跟踪 | string |  |
| message | 错误描述信息 | string |  |
| data | 分页数据 | IPageUserDto |  |
|   total | 总记录数 | integer(int64) |  |
|   current | 当前页码 | integer(int64) |  |
|   size | 每页条数 | integer(int64) |  |
|   pages | 总页数（已废弃） | integer(int64) |  |
|   records | 用户列表 | array | UserDto |
| tid | 跟踪唯一标识 | string |  |
| success |  | boolean |  |

**响应示例**:

```javascript
{
	"code": "0000",
	"displayCode": "0000",
	"message": "成功",
	"data": {
		"total": 795,
		"current": 1,
		"size": 10,
		"records": [
			{
				"id": 1776075291,
				"uid": "",
				"tenantId": 1,
				"userName": "双联系方式用户",
				"nickName": "",
				"avatar": "",
				"password": null,
				"resetPass": 1,
				"status": "Enabled",
				"role": "User",
				"email": "both@example.com",
				"phone": "13800000003",
				"lastLoginTime": null,
				"lang": "zh-CN",
				"created": "2026-04-13T10:14:56.000+00:00",
				"modified": "2026-04-13T10:14:56.000+00:00",
				"langMap": {}
			}
		]
	},
	"tid": "",
	"success": true
}
```

**CURL示例**

```shell
curl 'http://127.0.0.1:8081/api/v1/system/user/list' \
  -X POST \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY' \
  --data-raw '{
  "pageNo": 1,
  "pageSize": 10
}'

{"code":"0000","displayCode":"0000","message":"成功","data":{"total":795,"current":1,"size":10,"records":[...]},"tid":"...","success":true}
```

**测试用例**

| # | 场景 | 请求体 | total | 结果 |
| --- | --- | --- | --- | --- |
| 1 | 默认分页查询 | pageNo:1, pageSize:10 | 795 | 成功，返回10条记录 |
| 2 | 按状态过滤 | status: Disabled | 1 | 成功，返回禁用用户 |
| 3 | 按角色过滤 | role: Admin | 39 | 成功，返回管理员列表 |
| 4 | 按用户名模糊搜索 | userName: 测试 | 1 | 成功，匹配到包含"测试"的用户 |
| 5 | 查询第2页 | pageNo:2, pageSize:3 | 795 | 成功，current为2，返回3条 |
| 6 | 组合条件查询 | role: Admin, status: Enabled | 39 | 成功，返回启用的管理员 |

#### 按状态过滤

```shell
curl 'http://127.0.0.1:8081/api/v1/system/user/list' \
  -X POST \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY' \
  --data-raw '{
  "pageNo": 1,
  "pageSize": 5,
  "queryFilter": {"status": "Disabled"}
}'

{"code":"0000","displayCode":"0000","message":"成功","data":{"total":1,"current":1,"size":5,"records":[...]},"tid":"...","success":true}
```

#### 组合条件查询

```shell
curl 'http://127.0.0.1:8081/api/v1/system/user/list' \
  -X POST \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY' \
  --data-raw '{
  "pageNo": 1,
  "pageSize": 5,
  "queryFilter": {"role": "Admin", "status": "Enabled"}
}'

{"code":"0000","displayCode":"0000","message":"成功","data":{"total":39,"current":1,"size":5,"records":[...]},"tid":"...","success":true}
```

**TS模板示例**

```ts
// 查询过滤条件
export interface UserQueryDto {
  /* 用户姓名 */
  userName?: string;
  /* 昵称 */
  nickName?: string;
  /* 邮箱 */
  email?: string;
  /* 手机号码 */
  phone?: string;
  /* 用户状态: Enabled, Disabled */
  status?: 'Enabled' | 'Disabled';
  /* 角色: Admin, User */
  role?: 'Admin' | 'User';
}

// 分页查询请求
export interface UserListQuery {
  /* 页码 */
  pageNo: number;
  /* 每页条数 */
  pageSize: number;
  /* 查询过滤条件 */
  queryFilter?: UserQueryDto;
}

// 分页响应数据
export interface IPageUserDto {
  /* 总记录数 */
  total: number;
  /* 当前页码 */
  current: number;
  /* 每页条数 */
  size: number;
  /* 总页数（已废弃） */
  pages: number;
  /* 用户列表 */
  records: UserDto[];
}

// 响应接口
export interface UserListRes {
  code: string;
  displayCode: string;
  message: string;
  data: IPageUserDto;
  tid: string;
  success: boolean;
}

/** 
 * 分页查询用户列表
 * @param {UserListQuery} params 
 * @returns
 */
export function getUserList(params: UserListQuery): Promise<UserListRes> {
  return request.post(`/api/v1/system/user/list`, params);
}
```
