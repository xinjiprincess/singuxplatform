# 查询会话文件列表

> 更新：2026-10-04。本章为功能与操作参考，实际菜单取决于服务器授权和环境配置。界面存在不表示生产能力已验收，环境边界以项目操作指南为准。 接口未对线上执行写入验证；服务地址与密钥需替换为实际值。

## 接口信息

**接口地址**:`/api/v1/chat/{conversationId}/files`

**请求方式**:`GET`

**请求数据类型**:`无`

**响应数据类型**:`*/*`

**接口描述**:

查询指定会话中的文件列表

**请求示例**:

```
GET /api/v1/chat/1545555/files
```

## 请求参数

**请求头**

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
| --- | --- | --- | --- | --- |
| Authorization | string | 是 | API Key | `Bearer ak-REPLACE_WITH_API_KEY` |

**路径参数**:

| 参数名称 | 参数说明 | 是否必须 | 数据类型 |
| --- | --- | --- | --- |
| conversationId | 会话ID | 是 | integer(int64) |

**响应参数**:

| 参数名称 | 参数说明 | 类型 | schema |
| --- | --- | --- | --- |
| code | 业务状态码，0000 表示成功，其余失败 | string |  |
| displayCode | 源系统状态码，用于问题跟踪 | string |  |
| message | 错误描述信息 | string |  |
| data | 文件列表数据 | object | ComputerFileListRes |
|   files | 文件列表 | array | FileItem |
|     name | 文件路径 | string |  |
|     isDir | 是否为目录 | boolean |  |
|     fileProxyUrl | 文件代理URL | string |  |
|     isLink | 是否为链接 | boolean |  |
| tid | 跟踪唯一标识 | string |  |
| success |  | boolean |  |

**响应示例**:

```javascript
{
	"code": "0000",
	"displayCode": "0000",
	"message": "success",
	"data": {
		"files": [
			{
				"name": "html/index.html",
				"isDir": false,
				"fileProxyUrl": "/api/v1/chat/1544687/file/html/index.html",
				"isLink": false
			}
		]
	},
	"tid": "4730801776086909275",
	"success": true
}
```

**CURL示例**

```shell
curl 'http://127.0.0.1:8081/api/v1/chat/1544687/files' \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY'

{"code":"0000","displayCode":"0000","message":"success","data":{"files":[{"name":"html/index.html","isDir":false,"fileProxyUrl":"/api/v1/chat/1544687/file/html/index.html","isLink":false}]},"tid":"4730801776086909275","success":true}
```

**测试用例**

| # | 场景 | 状态码 | 结果 |
| --- | --- | --- | --- |
| 1 | 查询会话文件列表 | 0000 | 成功，返回文件列表（无文件时为空） |

**TS模板示例**

```ts
// 文件项
export interface FileItem {
  /* 文件路径 */
  name: string;
  /* 是否为目录 */
  isDir: boolean;
  /* 文件代理URL */
  fileProxyUrl: string;
  /* 是否为链接 */
  isLink: boolean;
}

// 文件列表响应
export interface ComputerFileListRes {
  /* 文件列表 */
  files: FileItem[];
}

// 响应接口
export interface ConversationFilesRes {
  code: string;
  displayCode: string;
  message: string;
  data: ComputerFileListRes;
  tid: string;
  success: boolean;
}

/** 
 * 查询会话文件列表
 * @param {number} conversationId - 会话ID
 * @returns
 */
export function getConversationFiles(conversationId: number): Promise<ConversationFilesRes> {
  return request.get(`/api/v1/chat/${conversationId}/files`);
}
```
