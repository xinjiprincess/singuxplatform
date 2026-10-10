# 查询用户详细信息

> 更新：2026-10-04。本章为功能与操作参考，实际菜单取决于服务器授权和环境配置。界面存在不表示生产能力已验收，环境边界以项目操作指南为准。 接口未对线上执行写入验证；服务地址与密钥需替换为实际值。

## 接口信息

**接口地址**:`/api/v1/system/user/detail`

**请求方式**:`GET`

**请求数据类型**:`application/x-www-form-urlencoded`

**响应数据类型**:`*/*`

**接口描述**:

通过 uid、id、username、email、phone 中任一条件查询用户详细信息

**请求示例**:

```
GET /api/v1/system/user/detail?id=1776073061
GET /api/v1/system/user/detail?uid=test_user_001
GET /api/v1/system/user/detail?email=test@example.com
```

## 请求参数

**请求头**

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
| --- | --- | --- | --- | --- |
| Authorization | string | 是 | API Key | `Bearer ak-REPLACE_WITH_API_KEY` |

**查询参数**:

| 参数名称 | 参数说明 | 是否必须 | 数据类型 |
| --- | --- | --- | --- |
| uid | 用户唯一标识 | 否 | string |
| id | 用户ID | 否 | integer(int64) |
| username | 用户名 | 否 | string |
| email | 邮箱 | 否 | string |
| phone | 手机号码 | 否 | string |

> 注：以上参数至少传入一个，不传任何参数会返回 `4000: Invalid param`

**响应参数**:

| 参数名称 | 参数说明 | 类型 | schema |
| --- | --- | --- | --- |
| code | 业务状态码，0000 表示成功，其余失败 | string |  |
| displayCode | 源系统状态码，用于问题跟踪 | string |  |
| message | 错误描述信息 | string |  |
| data | 用户详细信息 | UserDto |  |
|   id | 用户ID | integer(int64) |  |
|   uid | 用户唯一标识 | string |  |
|   tenantId | 商户ID | integer(int64) |  |
|   userName | 用户名 | string |  |
|   nickName | 用户昵称 | string |  |
|   avatar | 用户头像 | string |  |
|   password | 用户密码（返回为null） | string |  |
|   resetPass | 是否设置过密码，1表示已设置，0表示未设置 | integer(int32) |  |
|   status | 用户状态，可用值: Enabled, Disabled | string |  |
|   role | 角色，可用值: Admin, User | string |  |
|   email | 邮箱 | string |  |
|   phone | 手机号码 | string |  |
|   lastLoginTime | 最后登录时间 | string(date-time) |  |
|   lang | 最近的语言环境 | string |  |
|   created | 创建时间 | string(date-time) |  |
|   modified | 更新时间 | string(date-time) |  |
|   langMap | 语言环境对应的值映射 | object |  |
| tid | 跟踪唯一标识 | string |  |
| success |  | boolean |  |

**响应示例**:

```javascript
{
	"code": "0000",
	"displayCode": "0000",
	"message": "success",
	"data": {
		"id": 1776073061,
		"uid": "test_user_001",
		"tenantId": 1,
		"userName": "测试用户",
		"nickName": "测试昵称",
		"avatar": "",
		"password": null,
		"resetPass": 1,
		"status": "Enabled",
		"role": "User",
		"email": "test@example.com",
		"phone": "13800000001",
		"lastLoginTime": null,
		"lang": "zh-CN",
		"created": "2026-04-13T09:37:41.000+00:00",
		"modified": "2026-04-13T10:25:36.000+00:00",
		"langMap": {}
	},
	"tid": "6527691776075950763",
	"success": true
}
```

**CURL示例**

```shell
curl 'http://127.0.0.1:8081/api/v1/system/user/detail?id=1776073061' \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY'

{"code":"0000","displayCode":"0000","message":"success","data":{"id":1776073061,"uid":"test_user_001","tenantId":1,"userName":"测试用户","nickName":"测试昵称","avatar":"","password":null,"resetPass":1,"status":"Enabled","role":"User","email":"test@example.com","phone":"13800000001","lastLoginTime":null,"lang":"zh-CN","created":"2026-04-13T09:37:41.000+00:00","modified":"2026-04-13T10:25:36.000+00:00","langMap":{}},"tid":"615061776075295649","success":true}
```

**测试用例**

| # | 场景 | 查询条件 | 状态码 | 结果 |
| --- | --- | --- | --- | --- |
| 1 | 通过 ID 查询 | id=1776073061 | 0000 | 成功 |
| 2 | 通过 uid 查询 | uid=test\_user\_001 | 0000 | 成功 |
| 3 | 通过 email 查询 | [email=test@example.com](mailto:email=test@example.com) | 0000 | 成功 |
| 4 | 通过 phone 查询 | phone=13800000001 | 0000 | 成功 |
| 5 | 通过 username 查询 | username=测试用户 | 0000 | 成功 |
| 6 | 不传任何参数 | 无 | 4000 | 失败，返回 Invalid param |
| 7 | 查询不存在的用户 | id=99999999 | 4000 | 失败，返回 Invalid param |

#### 失败用例

**未传查询参数**

```shell
curl 'http://127.0.0.1:8081/api/v1/system/user/detail' \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY'

{"code":"4000","displayCode":"4000","message":"Invalid param","data":null,"tid":"8415441776075972669","success":false}
```

**查询不存在的用户**

```shell
curl 'http://127.0.0.1:8081/api/v1/system/user/detail?id=99999999' \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY'

{"code":"4000","displayCode":"4000","message":"Invalid param","data":null,"tid":"7125301776076289277","success":false}
```

**TS模板示例**

```ts
// 响应接口
export interface UserDto {
  /* 用户ID */
  id: number;
  /* 用户唯一标识 */
  uid: string;
  /* 商户ID */
  tenantId: number;
  /* 用户名 */
  userName: string;
  /* 用户昵称 */
  nickName: string;
  /* 用户头像 */
  avatar: string;
  /* 用户密码（通常为null） */
  password: string | null;
  /* 是否设置过密码，1表示已设置 */
  resetPass: number;
  /* 用户状态: Enabled, Disabled */
  status: 'Enabled' | 'Disabled';
  /* 角色: Admin, User */
  role: 'Admin' | 'User';
  /* 邮箱 */
  email: string;
  /* 手机号码 */
  phone: string;
  /* 最后登录时间 */
  lastLoginTime: string | null;
  /* 最近的语言环境 */
  lang: string;
  /* 创建时间 */
  created: string;
  /* 更新时间 */
  modified: string;
  /* 语言环境对应的值映射 */
  langMap: Record<string, string>;
}

export interface UserDetailRes {
  code: string;
  displayCode: string;
  message: string;
  data: UserDto | null;
  tid: string;
  success: boolean;
}

/** 
 * 查询用户详细信息
 * @param {object} params - 查询条件，id/uid/username/email/phone 至少传入一个
 * @param {number} [params.id] - 用户ID
 * @param {string} [params.uid] - 用户唯一标识
 * @param {string} [params.username] - 用户名
 * @param {string} [params.email] - 邮箱
 * @param {string} [params.phone] - 手机号码
 * @returns
 */
export function getUserDetail(params: {
  id?: number;
  uid?: string;
  username?: string;
  email?: string;
  phone?: string;
}): Promise<UserDetailRes> {
  return request.get(`/api/v1/system/user/detail`, { params });
}
```
