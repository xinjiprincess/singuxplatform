# 获取文件访问AK

> 更新：2026-10-04。本章为功能与操作参考，实际菜单取决于服务器授权和环境配置。界面存在不表示生产能力已验收，环境边界以项目操作指南为准。 接口未对线上执行写入验证；服务地址与密钥需替换为实际值。

## 接口信息

**接口地址**:`/api/v1/file/ak`

**请求方式**:`GET`

**请求数据类型**:`无`

**响应数据类型**:`*/*`

**接口描述**:

获取文件的临时访问链接（带 AK 签名），用于访问私有存储的文件

**请求示例**:

```
GET /api/v1/file/ak?fileUrl=https://service.example.invalid
```

## 请求参数

**请求头**

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
| --- | --- | --- | --- | --- |
| Authorization | string | 是 | API Key | `Bearer ak-REPLACE_WITH_API_KEY` |

**查询参数**:

| 参数名称 | 参数说明 | 是否必须 | 数据类型 |
| --- | --- | --- | --- |
| fileUrl | 文件URL | 是 | string |

**响应参数**:

| 参数名称 | 参数说明 | 类型 | schema |
| --- | --- | --- | --- |
| code | 业务状态码，0000 表示成功，其余失败 | string |  |
| displayCode | 源系统状态码，用于问题跟踪 | string |  |
| message | 错误描述信息 | string |  |
| data | 带签名的文件访问URL | string |  |
| tid | 跟踪唯一标识 | string |  |
| success |  | boolean |  |

**响应示例**:

```javascript
{
	"code": "0000",
	"displayCode": "0000",
	"message": "success",
	"data": "https://service.example.invalid",
	"tid": "9542251776087397235",
	"success": true
}
```

**CURL示例**

```shell
curl 'http://127.0.0.1:8081/api/v1/file/ak?fileUrl=https://service.example.invalid' \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY'

{"code":"0000","displayCode":"0000","message":"success","data":"https://...","tid":"9542251776087397235","success":true}
```

**TS模板示例**

```ts
// 响应接口
export interface FileAkRes {
  code: string;
  displayCode: string;
  message: string;
  data: string;
  tid: string;
  success: boolean;
}

/** 
 * 获取文件访问AK（带签名的临时访问链接）
 * @param {string} fileUrl - 文件URL
 * @returns
 */
export function getFileAk(fileUrl: string): Promise<FileAkRes> {
  return request.get(`/api/v1/file/ak?fileUrl=${encodeURIComponent(fileUrl)}`);
}
```
