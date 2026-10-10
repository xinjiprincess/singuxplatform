# 文件上传

> 更新：2026-10-04。本章为功能与操作参考，实际菜单取决于服务器授权和环境配置。界面存在不表示生产能力已验收，环境边界以项目操作指南为准。 接口未对线上执行写入验证；服务地址与密钥需替换为实际值。

## 接口信息

**接口地址**:`/api/v1/file/upload`

**请求方式**:`POST`

**请求数据类型**:`multipart/form-data`

**响应数据类型**:`*/*`

**接口描述**:

文件上传接口，上传后返回文件网络地址

**请求示例**:

```
POST /api/v1/file/upload?type=tmp
Content-Type: multipart/form-data

file: (binary)
```

## 请求参数

**请求头**

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
| --- | --- | --- | --- | --- |
| Authorization | string | 是 | API Key | `Bearer ak-REPLACE_WITH_API_KEY` |

**查询参数**:

| 参数名称 | 参数说明 | 是否必须 | 数据类型 | 默认值 |
| --- | --- | --- | --- | --- |
| type | 存储类型，tmp 临时文件；store 永久存储 | 否 | string | tmp |

**表单参数**:

| 参数名称 | 参数说明 | 是否必须 | 数据类型 |
| --- | --- | --- | --- |
| file | 文件二进制 | 是 | file |

**响应参数**:

| 参数名称 | 参数说明 | 类型 | schema |
| --- | --- | --- | --- |
| code | 业务状态码，0000 表示成功，其余失败 | string |  |
| displayCode | 源系统状态码，用于问题跟踪 | string |  |
| message | 错误描述信息 | string |  |
| data | 文件上传结果 | object | UploadResultDto |
|   url | 文件完整的网络地址 | string |  |
|   key | 文件唯一标识 | string |  |
|   fileName | 文件名称 | string |  |
|   mimeType | 文件类型 | string |  |
|   size | 文件大小（字节） | integer(int32) |  |
|   width | 图片宽度 | integer(int32) |  |
|   height | 图片高度 | integer(int32) |  |
| tid | 跟踪唯一标识 | string |  |
| success |  | boolean |  |

**响应示例**:

```javascript
{
	"code": "0000",
	"displayCode": "0000",
	"message": "success",
	"data": {
		"url": "https://service.example.invalid",
		"key": "tmp/f7dce62d43d142559772c0bd01b20e36.txt",
		"fileName": "test_upload.txt",
		"mimeType": "text/plain",
		"size": 18,
		"width": 0,
		"height": 0
	},
	"tid": "7383371776087252690",
	"success": true
}
```

**CURL示例**

```shell
# 上传临时文件
curl 'http://127.0.0.1:8081/api/v1/file/upload?type=tmp' \
  -X POST \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY' \
  -F 'file=@/path/to/your/file.txt'

# 上传永久存储文件
curl 'http://127.0.0.1:8081/api/v1/file/upload?type=store' \
  -X POST \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY' \
  -F 'file=@/path/to/your/image.png'
```

**测试用例**

| # | 场景 | 状态码 | 结果 |
| --- | --- | --- | --- |
| 1 | 上传临时文件（type=tmp） | 0000 | 成功，返回临时文件URL |
| 2 | 上传永久存储文件（type=store） | 0000 | 成功，返回永久文件URL |

**TS模板示例**

```ts
// 文件上传结果
export interface UploadResultDto {
  /* 文件完整的网络地址 */
  url: string;
  /* 文件唯一标识 */
  key: string;
  /* 文件名称 */
  fileName: string;
  /* 文件类型 */
  mimeType: string;
  /* 文件大小（字节） */
  size: number;
  /* 图片宽度 */
  width: number;
  /* 图片高度 */
  height: number;
}

// 响应接口
export interface FileUploadRes {
  code: string;
  displayCode: string;
  message: string;
  data: UploadResultDto;
  tid: string;
  success: boolean;
}

/** 
 * 文件上传
 * @param {File} file - 文件对象
 * @param {'tmp' | 'store'} type - 存储类型
 * @returns
 */
export function uploadFile(file: File, type: 'tmp' | 'store' = 'tmp'): Promise<FileUploadRes> {
  const formData = new FormData();
  formData.append('file', file);
  return request.post(`/api/v1/file/upload?type=${type}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
}
```
