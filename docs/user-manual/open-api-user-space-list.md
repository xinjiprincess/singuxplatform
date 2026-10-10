# 查询用户空间列表

> 更新：2026-10-04。本章为功能与操作参考，实际菜单取决于服务器授权和环境配置。界面存在不表示生产能力已验收，环境边界以项目操作指南为准。 接口未对线上执行写入验证；服务地址与密钥需替换为实际值。

## 接口信息

**接口地址**:`/api/v1/system/user/{id}/space/list`

**请求方式**:`GET`

**请求数据类型**:`无`

**响应数据类型**:`*/*`

**接口描述**:

通过用户ID查询该用户所在的空间列表

**请求示例**:

```
GET /api/v1/system/user/1776073061/space/list
```

## 请求参数

**请求头**

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
| --- | --- | --- | --- | --- |
| Authorization | string | 是 | API Key | `Bearer ak-REPLACE_WITH_API_KEY` |

**路径参数**:

| 参数名称 | 参数说明 | 是否必须 | 数据类型 |
| --- | --- | --- | --- |
| id | 用户ID | 是 | integer(int64) |

**响应参数**:

| 参数名称 | 参数说明 | 类型 | schema |
| --- | --- | --- | --- |
| code | 业务状态码，0000 表示成功，其余失败 | string |  |
| displayCode | 源系统状态码，用于问题跟踪 | string |  |
| message | 错误描述信息 | string |  |
| data | 空间列表 | array | SpaceDto |
|   id | 空间ID | integer(int64) |  |
|   tenantId | 租户ID | integer(int64) |  |
|   name | 空间名称 | string |  |
|   description | 空间描述 | string |  |
|   icon | 空间图标 | string |  |
|   type | 空间类型，可用值: Personal, Team, Class | string |  |
|   creatorId | 创建者ID | integer(int64) |  |
|   creatorName | 创建者名称 | string |  |
|   modified | 更新时间 | string(date-time) |  |
|   created | 创建时间 | string(date-time) |  |
|   currentUserRole | 当前用户在空间的角色，可用值: Owner, Admin, User | string |  |
|   receivePublish | 空间是否接收来自外部的发布 | integer(int32) |  |
|   allowDevelop | 空间是否开启开发功能 | integer(int32) |  |
| tid | 跟踪唯一标识 | string |  |
| success |  | boolean |  |

**响应示例**:

```javascript
{
	"code": "0000",
	"displayCode": "0000",
	"message": "success",
	"data": [
		{
			"id": 1066,
			"tenantId": 1,
			"name": "个人空间",
			"description": null,
			"icon": null,
			"type": "Personal",
			"creatorId": 1776073061,
			"creatorName": "更新后的用户名",
			"modified": "2026-04-13T09:37:41.000+00:00",
			"created": "2026-04-13T09:37:41.000+00:00",
			"currentUserRole": null,
			"receivePublish": 0,
			"allowDevelop": 0
		}
	],
	"tid": "123456789",
	"success": true
}
```

**CURL示例**

```shell
curl 'http://127.0.0.1:8081/api/v1/system/user/1776073061/space/list' \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY'

{"code":"0000","displayCode":"0000","message":"success","data":[{"id":1066,"tenantId":1,"name":"个人空间","type":"Personal","creatorId":1776073061,"creatorName":"更新后的用户名","modified":"2026-04-13T09:37:41.000+00:00","created":"2026-04-13T09:37:41.000+00:00","receivePublish":0,"allowDevelop":0}],"tid":"123456789","success":true}
```

**测试用例**

| # | 场景 | 状态码 | 结果 |
| --- | --- | --- | --- |
| 1 | 查询已有用户的空间列表 | 0000 | 成功，返回1个个人空间 |
| 2 | 查询不存在的用户 | 0000 | 成功，返回空数组 |

**TS模板示例**

```ts
// 空间信息
export interface SpaceDto {
  /* 空间ID */
  id: number;
  /* 租户ID */
  tenantId: number;
  /* 空间名称 */
  name: string;
  /* 空间描述 */
  description: string | null;
  /* 空间图标 */
  icon: string | null;
  /* 空间类型: Personal, Team, Class */
  type: 'Personal' | 'Team' | 'Class';
  /* 创建者ID */
  creatorId: number;
  /* 创建者名称 */
  creatorName: string;
  /* 更新时间 */
  modified: string;
  /* 创建时间 */
  created: string;
  /* 当前用户在空间的角色: Owner, Admin, User */
  currentUserRole: 'Owner' | 'Admin' | 'User' | null;
  /* 是否接收来自外部的发布 */
  receivePublish: number;
  /* 是否开启开发功能 */
  allowDevelop: number;
}

// 响应接口
export interface UserSpaceListRes {
  code: string;
  displayCode: string;
  message: string;
  data: SpaceDto[];
  tid: string;
  success: boolean;
}

/** 
 * 查询用户空间列表
 * @param {number} id - 用户ID
 * @returns
 */
export function getUserSpaceList(id: number): Promise<UserSpaceListRes> {
  return request.get(`/api/v1/system/user/${id}/space/list`);
}
```
