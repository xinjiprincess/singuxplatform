# 更新用户信息

> 更新：2026-10-04。本章为功能与操作参考，实际菜单取决于服务器授权和环境配置。界面存在不表示生产能力已验收，环境边界以项目操作指南为准。 接口未对线上执行写入验证；服务地址与密钥需替换为实际值。

## 接口信息

**接口地址**:`/api/v1/system/user/{id}/update`

**请求方式**:`POST`

**请求数据类型**:`application/json`

**响应数据类型**:`*/*`

**接口描述**:

通过用户ID更新用户信息

**请求示例**:

```javascript
{
  "userName": "更新后的用户名",
  "nickName": "更新后的昵称",
  "avatar": "https://example.com/avatar.png",
  "role": "User",
  "email": "updated@example.com",
  "phone": "13800000099"
}
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

**请求体参数**:

| 参数名称 | 参数说明 | 是否必须 | 数据类型 |
| --- | --- | --- | --- |
| userName | 用户名 | 否 | string |
| nickName | 用户昵称 | 否 | string |
| avatar | 用户头像地址 | 否 | string |
| role | 角色，可用值: Admin, User | 否 | string |
| email | 管理员邮箱 | 否 | string |
| phone | 手机号码 | 否 | string |
| password | 密码 | 否 | string |

**响应参数**:

| 参数名称 | 参数说明 | 类型 | schema |
| --- | --- | --- | --- |
| code | 业务状态码，0000 表示成功，其余失败 | string |  |
| displayCode | 源系统状态码，用于问题跟踪 | string |  |
| message | 错误描述信息 | string |  |
| data | 返回的具体业务数据 | object |  |
| tid | 跟踪唯一标识 | string |  |
| success |  | boolean |  |

**响应示例**:

```javascript
{
	"code": "0000",
	"displayCode": "0000",
	"message": "成功",
	"data": null,
	"tid": "1647851776076494587",
	"success": true
}
```

**CURL示例**

```shell
curl 'http://127.0.0.1:8081/api/v1/system/user/1776073061/update' \
  -X POST \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY' \
  --data-raw '{
  "userName": "更新后的用户名",
  "nickName": "更新后的昵称",
  "avatar": "https://example.com/avatar.png",
  "role": "User",
  "email": "updated@example.com",
  "phone": "13800000099"
}'

{"code":"0000","displayCode":"0000","message":"成功","data":null,"tid":"1647851776076494587","success":true}
```

**测试用例**

| # | 场景 | 请求体 | 状态码 | 结果 |
| --- | --- | --- | --- | --- |
| 1 | 更新用户基本信息 | userName + nickName + avatar + email + phone + role | 0000 | 成功 |
| 2 | 更新密码 | password | 0000 | 成功 |
| 3 | 更新不存在的用户 | userName | 0000 | 成功 |
| 4 | 空 body 更新 | {} | 4000 | 失败，提示字段不能同时为空 |
| 5 | 更新角色为 Admin | role: Admin | 0000 | 成功 |

#### 成功用例

**更新用户基本信息**

```shell
curl 'http://127.0.0.1:8081/api/v1/system/user/1776073061/update' \
  -X POST \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY' \
  --data-raw '{
  "userName": "更新后的用户名",
  "nickName": "更新后的昵称",
  "avatar": "https://example.com/avatar.png",
  "role": "User",
  "email": "updated@example.com",
  "phone": "13800000099"
}'

{"code":"0000","displayCode":"0000","message":"成功","data":null,"tid":"1647851776076494587","success":true}
```

**更新角色**

```shell
curl 'http://127.0.0.1:8081/api/v1/system/user/1776073061/update' \
  -X POST \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY' \
  --data-raw '{"role": "Admin"}'

{"code":"0000","displayCode":"0000","message":"成功","data":null,"tid":"5342371776076658883","success":true}
```

#### 失败用例

**空 body 更新**

```shell
curl 'http://127.0.0.1:8081/api/v1/system/user/1776073061/update' \
  -X POST \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY' \
  --data-raw '{}'

{"code":"4000","displayCode":"4000","message":"nickName, userName, email, phone, avatar, role, password  cannot be null at the same time","data":null,"tid":"8803401776078516945","success":false}
```

**TS模板示例**

```ts
// 参数接口
export interface UserUpdateDto {
  /* 用户名 */
  userName?: string;
  /* 用户昵称 */
  nickName?: string;
  /* 用户头像地址 */
  avatar?: string;
  /* 角色，可用值: Admin, User */
  role?: 'Admin' | 'User';
  /* 管理员邮箱 */
  email?: string;
  /* 手机号码 */
  phone?: string;
  /* 密码 */
  password?: string;
}

// 响应接口
export interface UpdateUserRes {
  code: string;
  displayCode: string;
  message: string;
  data: object | null;
  tid: string;
  success: boolean;
}

/** 
 * 更新用户信息
 * @param {number} id - 用户ID
 * @param {UserUpdateDto} params 
 * @returns
 */
export function updateUser(id: number, params: UserUpdateDto): Promise<UpdateUserRes> {
  return request.post(`/api/v1/system/user/${id}/update`, params);
}
```
