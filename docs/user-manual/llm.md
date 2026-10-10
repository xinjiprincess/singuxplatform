# 大模型接入

> 更新：2026-10-04。本章为功能与操作参考，实际菜单取决于服务器授权和环境配置。界面存在不表示生产能力已验收，环境边界以项目操作指南为准。

## 智谱GLM模型

1.  首先到**智谱AI平台**获取[API Key](https://bigmodel.cn/usercenter/proj-mgmt/apikeys)
2.  根据智谱GLM的[API文档](https://docs.bigmodel.cn/cn/guide/start/introduction)进行配置
3.  常用协议
    -   **OpenAI**的API参考文档[OpenAI](https://docs.bigmodel.cn/cn/guide/develop/openai/introduction#openai-api)
    -   **Anthropic**的API参考文档[Anthropic](https://docs.bigmodel.cn/cn/guide/develop/goose#%E4%B8%89%E3%80%81%E9%80%89%E6%8B%A9-anthropic-%E5%8D%8F%E8%AE%AE%E5%B9%B6%E9%85%8D%E7%BD%AE)
    -   [GLM编码套餐](https://docs.bigmodel.cn/cn/coding-plan/tool/others)，购买套餐后的使用方法就和普通模型的导入方式相同，只是需要注意OpenAI Base URL的地址需要替换成`https://open.bigmodel.cn/api/coding/paas/v4`

## MiniMax

1.  首先到**MiniMax平台**获取[API Key](https://platform.minimaxi.com/user-center/basic-information/interface-key)
2.  根据MiniMax的[API文档](https://platform.minimaxi.com/docs/guides/models-intro)进行配置
3.  OpenAI API 兼容[文档](https://platform.minimaxi.com/docs/api-reference/text-openai-api#openai-api)
4.  Anthropic API 兼容[文档](https://platform.minimaxi.com/docs/api-reference/text-anthropic-api#anthropic-api)

## 通义千问模型

1.  首先到**阿里云百炼大模型服务平台**（通义千问是阿里云旗下模型，百炼是其服务平台）获取[API Key](https://bailian.console.aliyun.com/?tab=model#/api-key)
2.  根据通义千问的[API文档](https://bailian.console.aliyun.com/console?tab=api#/api/?type=model&url=https%3A%2F%2Fhelp.aliyun.com%2Fdocument_detail%2F2712576.html&renderType=iframe)找到调用模型的接口
3.  在[智能体平台](https://agent.xspaceagi.com/)点击**组件库**，找到**组件**，点击创建**模型**
    -   **模型名称**：可以按照需求给模型命名
    -   **模型标识**：这是模型的唯一标识，在一些模型的API文档中也通常称为模型名，如，qwq-plus、qwen-max、qwen-turbo等
    -   **模型介绍**：可简单描述模型特点
    -   **模型类型**：可根据模型选择**聊天对话-纯文本**、**聊天对话-多模态**和**向量嵌入**
    -   **推理模型**：根据模型特点选择是否是推理模型
    -   **最大输出token数**：模型在一次生成回答时，所能输出的最大 token 数量上限。通常 100 token约等于150个中文汉字。**对于通用型智能体，请务必设置足够大的最大输出token，否则可能导致智能体无法完整执行并输出结果。**

> **⚠️ 重要提示**：请正确设置模型最大支持的token输出数量，过小的输出token可能导致无法生成结果文件。

-   **函数调用支持**：是指模型通过特定的格式（通常是结构化的 JSON）生成指令，调用外部工具、API 接口或自定义函数，以获取信息、执行操作或完成复杂任务的能力。可以设置为**支持普通函数调用**、**支持流式函数调用**和**不支持函数调用**
-   **接口协议**：平台提供市面上流行的接口协议，如，**OpenAI**、**Ollama**、**Anthropic**等
-   **接口配置**：
    -   **URL**：大模型的请求接口，可以通过阅读模型API文档获取
    -   **API KEY**：通过模型平台获取
    -   **权重**：当接口配置多个大模型时，权重值设置越大调用的概率越高

4.  测试新增的**千问MAX模型**
