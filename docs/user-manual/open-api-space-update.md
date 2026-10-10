# 更新团队空间

> 更新：2026-10-04。本章为功能与操作参考，实际菜单取决于服务器授权和环境配置。界面存在不表示生产能力已验收，环境边界以项目操作指南为准。 接口未对线上执行写入验证；服务地址与密钥需替换为实际值。

## 接口信息

**接口地址**:`/api/v1/space/{id}/update`

**请求方式**:`POST`

**请求数据类型**:`application/json`

**响应数据类型**:`*/*`

**接口描述**:

更新团队空间信息。路径参数和请求体中均需要传入空间ID。

**请求示例**:

```javascript
{
  "id": 1071,
  "name": "更新后的测试团队空间",
  "description": "更新后的描述",
  "icon": "https://example.com/new-icon.png",
  "receivePublish": 1,
  "allowDevelop": 1
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
| id | 空间ID | 是 | integer(int64) |

**请求体参数**:

| 参数名称 | 参数说明 | 是否必须 | 数据类型 |
| --- | --- | --- | --- |
| id | 空间ID | 是 | integer(int64) |
| name | 空间名称 | 否 | string |
| description | 空间描述 | 否 | string |
| icon | 空间图标 | 否 | string |
| receivePublish | 空间是否接收来自外部的发布 | 否 | integer(int32) |
| allowDevelop | 空间是否开启开发功能 | 否 | integer(int32) |

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
	"tid": "7168311776083131283",
	"success": true
}
```

**CURL示例**

```shell
curl 'http://127.0.0.1:8081/api/v1/space/1071/update' \
  -X POST \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY' \
  --data-raw '{
  "id": 1071,
  "name": "更新后的测试团队空间",
  "description": "更新后的描述",
  "icon": "https://example.com/new-icon.png",
  "receivePublish": 1,
  "allowDevelop": 1
}'

{"code":"0000","displayCode":"0000","message":"成功","data":null,"tid":"7168311776083131283","success":true}
```

**测试用例**

| # | 场景 | 状态码 | 结果 |
| --- | --- | --- | --- |
| 1 | 完整参数更新空间 | 0000 | 成功 |
| 2 | 仅更新名称 | 0000 | 成功 |
| 3 | 请求体中缺少id | 4000 | 失败，提示"Space ID is required" |
| 4 | 更新不存在的空间 | 4030 | 失败，提示"无权限" |

#### 失败用例

**请求体中缺少id**

```shell
curl 'http://127.0.0.1:8081/api/v1/space/1071/update' \
  -X POST \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY' \
  --data-raw '{"name": "仅更新名称"}'

{"code":"4000","displayCode":"4000","message":"Space ID is required","data":null,"tid":"...","success":false}
```

**更新不存在的空间**

```shell
curl 'http://127.0.0.1:8081/api/v1/space/99999999/update' \
  -X POST \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY' \
  --data-raw '{"id": 99999999, "name": "不存在的空间"}'

{"code":"4030","displayCode":"4030","message":"无权限","data":null,"tid":"...","success":false}
```

**TS模板示例**

```ts
// 参数接口
export interface SpaceUpdateDto {
  /* 空间ID */
  id: number;
  /* 空间名称 */
  name?: string;
  /* 空间描述 */
  description?: string;
  /* 空间图标 */
  icon?: string;
  /* 是否接收来自外部的发布 */
  receivePublish?: number;
  /* 是否开启开发功能 */
  allowDevelop?: number;
}

// 响应接口
export interface UpdateSpaceRes {
  code: string;
  displayCode: string;
  message: string;
  data: object | null;
  tid: string;
  success: boolean;
}

/** 
 * 更新团队空间
 * @param {number} id - 空间ID
 * @param {SpaceUpdateDto} params 
 * @returns
 */
export function updateSpace(id: number, params: SpaceUpdateDto): Promise<UpdateSpaceRes> {
  return request.post(`/api/v1/space/${id}/update`, params);
}
```
