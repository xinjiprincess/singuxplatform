# 创建团队空间

> 更新：2026-10-04。本章为功能与操作参考，实际菜单取决于服务器授权和环境配置。界面存在不表示生产能力已验收，环境边界以项目操作指南为准。 接口未对线上执行写入验证；服务地址与密钥需替换为实际值。

## 接口信息

**接口地址**:`/api/v1/space/add`

**请求方式**:`POST`

**请求数据类型**:`application/json`

**响应数据类型**:`*/*`

**接口描述**:

创建团队空间

**请求示例**:

```javascript
{
  "name": "测试团队空间",
  "description": "用于测试的团队空间",
  "icon": "https://example.com/icon.png"
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
| name | 空间名称 | 是 | string |
| description | 空间描述 | 否 | string |
| icon | 空间图标 | 否 | string |

**响应参数**:

| 参数名称 | 参数说明 | 类型 | schema |
| --- | --- | --- | --- |
| code | 业务状态码，0000 表示成功，其余失败 | string |  |
| displayCode | 源系统状态码，用于问题跟踪 | string |  |
| message | 错误描述信息 | string |  |
| data | 创建的空间ID | integer(int64) |  |
| tid | 跟踪唯一标识 | string |  |
| success |  | boolean |  |

**响应示例**:

```javascript
{
	"code": "0000",
	"displayCode": "0000",
	"message": "success",
	"data": 1071,
	"tid": "2162841776083028814",
	"success": true
}
```

**CURL示例**

```shell
curl 'http://127.0.0.1:8081/api/v1/space/add' \
  -X POST \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY' \
  --data-raw '{
  "name": "测试团队空间",
  "description": "用于测试的团队空间",
  "icon": "https://example.com/icon.png"
}'

{"code":"0000","displayCode":"0000","message":"success","data":1071,"tid":"2162841776083028814","success":true}
```

**测试用例**

| # | 场景 | 请求要点 | 状态码 | 结果 |
| --- | --- | --- | --- | --- |
| 1 | 完整参数创建空间 | name + description + icon | 0000 | 成功，返回空间ID |
| 2 | 仅传名称创建空间 | name | 0000 | 成功，返回空间ID |
| 3 | 缺少必填字段name | 仅传description | 4000 | 失败，提示"Space name is required" |

#### 失败用例

**缺少必填字段**

```shell
curl 'http://127.0.0.1:8081/api/v1/space/add' \
  -X POST \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY' \
  --data-raw '{"description": "没有名称"}'

{"code":"4000","displayCode":"4000","message":"Space name is required","data":null,"tid":"9532751776083046187","success":false}
```

**TS模板示例**

```ts
// 参数接口
export interface SpaceAddDto {
  /* 空间名称 */
  name: string;
  /* 空间描述 */
  description?: string;
  /* 空间图标 */
  icon?: string;
}

// 响应接口
export interface AddSpaceRes {
  code: string;
  displayCode: string;
  message: string;
  data: number;
  tid: string;
  success: boolean;
}

/** 
 * 创建团队空间
 * @param {SpaceAddDto} params 
 * @returns
 */
export function addSpace(params: SpaceAddDto): Promise<AddSpaceRes> {
  return request.post(`/api/v1/space/add`, params);
}
```
