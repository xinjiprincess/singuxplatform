# 添加用户

> 更新：2026-10-04。本项目 userName 是登录名，nickName 是昵称。当前工具默认学校代号拼接学号，保留前导零；旧纯数字用户名需兼容补丁。导入只创建 User，默认检查 phone 和 email。 接口未对线上执行写入验证；服务地址与密钥需替换为实际值。

## 接口信息

**接口地址**:`/api/v1/system/user/add`

**请求方式**:`POST`

**请求数据类型**:`application/json`

**响应数据类型**:`*/*`

**接口描述**:

添加系统用户

**请求示例**:

```javascript
{
  "uid": "test_user_001",
  "phone": "13800000001",
  "password": "Test@123456",
  "userName": "测试用户",
  "nickName": "测试昵称",
  "avatar": "",
  "email": "test@example.com",
  "role": "User"
}
```

## 请求参数

**请求头**

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
| --- | --- | --- | --- | --- |
| Authorization | string | 是 | API Key | `Bearer ak-REPLACE_WITH_API_KEY` |

**请求参数**:

| 参数名称 | 参数说明 | 是否必须 | 数据类型 |
| --- | --- | --- | --- |
| uid | 用户唯一标识，可以记录三方账号系统唯一标识 | 否 | string |
| phone | 手机号码 | 是 | string |
| password | 密码 | 否 | string |
| userName | 登录用户名（工号/学号保留前导零） | 否 | string |
| nickName | 昵称 | 否 | string |
| avatar | 头像 | 否 | string |
| email | 邮箱 | 是 | string |
| role | 角色，可用值: Admin, User | 否 | string |

**响应参数**:

| 参数名称 | 参数说明 | 类型 | schema |
| --- | --- | --- | --- |
| code | 业务状态码，0000 表示成功，其余失败 | string |  |
| displayCode | 源系统状态码，用于问题跟踪 | string |  |
| message | 错误描述信息 | string |  |
| data | 创建的用户ID | integer(int64) | integer(int64) |
| tid | 跟踪唯一标识 | string |  |
| success |  | boolean |  |

**响应示例**:

```javascript
{
	"code": "0000",
	"displayCode": "0000",
	"message": "success",
	"data": 1776073061,
	"tid": "6194301776073060981",
	"success": true
}
```

**CURL示例**

```shell
curl 'http://127.0.0.1:8081/api/v1/system/user/add' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY' \
  --data-raw '{
  "uid": "test_user_001",
  "phone": "13800000001",
  "password": "Test@123456",
  "userName": "测试用户",
  "nickName": "测试昵称",
  "avatar": "",
  "email": "test@example.com",
  "role": "User"
}'

{"code":"0000","displayCode":"0000","message":"success","data":1776073061,"tid":"6194301776073060981","success":true}
```

**测试用例**

| # | 场景 | 参数要点 | 状态码 | 结果 |
| --- | --- | --- | --- | --- |
| 1 | 完整参数 | uid + phone + email + 其他 | 0000 | 成功 |
| 2 | 仅传手机号 | phone + userName + role | 4000 | 失败 |
| 3 | 仅传邮箱 | email + userName + role | 4000 | 失败 |
| 4 | 未传手机号和邮箱 | userName + role | 4000 | 失败 |
| 5 | 同时传手机号和邮箱 | phone + email + userName + role | 0000 | 成功 |
| 6 | Admin角色 | uid + phone + userName + role(Admin) | 4000 | 失败 |

> 注意：根据实际测试结果，**phone 和 email 必须同时传入**，单独传其中一个会返回 `4000: email and phone cannot be null at the same time`

#### 成功用例

**完整参数创建用户**

```shell
curl 'http://127.0.0.1:8081/api/v1/system/user/add' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY' \
  --data-raw '{
  "uid": "test_user_001",
  "phone": "13800000001",
  "password": "Test@123456",
  "userName": "测试用户",
  "nickName": "测试昵称",
  "avatar": "",
  "email": "test@example.com",
  "role": "User"
}'

{"code":"0000","displayCode":"0000","message":"success","data":1776073061,"tid":"6194301776073060981","success":true}
```

#### 失败用例

**phone 和 email 不能同时为空**

仅传 phone、仅传 email、或两者都不传，均返回：

```json
{"code":"4000","displayCode":"4000","message":"email and phone cannot be null at the same time","data":null,"tid":"615061776075295649","success":false}
```

#### 频率限制

短时间内频繁请求会触发每日请求次数限制：

```json
{"code":"4290","displayCode":"4290","message":"每日请求次数超限","data":null,"tid":"905131776073214575","success":false}
```

**TS模板示例**

```ts
// 参数接口
export interface UserAddDto {
  /*用户唯一标识，可以记录三方账号系统唯一标识 */
  uid?: string;
  /*手机号码 */
  phone?: string;
  /*密码 */
  password?: string;
  /*姓名 */
  userName?: string;
  /*昵称 */
  nickName?: string;
  /*头像 */
  avatar?: string;
  /*邮箱 */
  email?: string;
  /*角色，可用值: Admin, User */
  role?: 'Admin' | 'User';
}

// 响应接口
export interface AddUserRes {
  code: string;
  displayCode: string;
  message: string;
  data: number;
  tid: string;
  success: boolean;
}

/** 
 * 添加用户
 * @param {UserAddDto} params 
 * @returns
 */
export function addUser(params: UserAddDto): Promise<AddUserRes> {
  return request.post(`/api/v1/system/user/add`, params);
}
```
