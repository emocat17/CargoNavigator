# Dify 知识库与配置指南

## 知识库API使用

### API概述

通过API维护知识库可大幅提升数据处理效率，实现自动化操作，而无需在用户界面进行繁琐操作。

主要优势包括：
- 自动同步：将数据系统与Dify知识库无缝对接，构建高效工作流程
- 全面管理：提供知识库列表，文档列表及详情查询等功能
- 灵活上传：支持纯文本和文件上传方式，可针对分段内容的批量新增和修改操作
- 提高效率：减少手动处理时间，提升Dify平台使用体验

### API调用示例

#### 通过文本创建文档

```bash
curl --location --request POST 'https://api.dify.ai/v1/datasets/{dataset_id}/document/create_by_text' \
--header 'Authorization: Bearer {api_key}' \
--header 'Content-Type: application/json' \
--data-raw '{"name": "text","text": "text","indexing_technique": "high_quality","process_rule": {"mode": "automatic"}}'
```

#### 通过文件创建文档

```bash
curl --location --request POST 'https://api.dify.ai/v1/datasets/{dataset_id}/document/create_by_file' \
--header 'Authorization: Bearer {api_key}' \
--form 'data="{"indexing_technique":"high_quality","process_rule":{"rules":{"pre_processing_rules":[{"id":"remove_extra_spaces","enabled":true},{"id":"remove_urls_emails","enabled":true}],"segmentation":{"separator":"###","max_tokens":500}},"mode":"custom"}}";type=text/plain' \
--form 'file=@"/path/to/file"'
```

#### 创建空知识库

```bash
curl --location --request POST 'https://api.dify.ai/v1/datasets' \
--header 'Authorization: Bearer {api_key}' \
--header 'Content-Type: application/json' \
--data-raw '{"name": "name", "permission": "only_me"}'
```

#### 知识库列表

```bash
curl --location --request GET 'https://api.dify.ai/v1/datasets?page=1&limit=20' \
--header 'Authorization: Bearer {api_key}'
```

#### 删除知识库

```bash
curl --location --request DELETE 'https://api.dify.ai/v1/datasets/{dataset_id}' \
--header 'Authorization: Bearer {api_key}'
```

#### 获取文档嵌入状态

```bash
curl --location --request GET 'https://api.dify.ai/v1/datasets/{dataset_id}/documents/{batch}/indexing-status' \
--header 'Authorization: Bearer {api_key}'
```

#### 删除文档

```bash
curl --location --request DELETE 'https://api.dify.ai/v1/datasets/{dataset_id}/documents/{document_id}' \
--header 'Authorization: Bearer {api_key}'
```

#### 知识库文档列表

```bash
curl --location --request GET 'https://api.dify.ai/v1/datasets/{dataset_id}/documents' \
--header 'Authorization: Bearer {api_key}'
```

#### 新增分段

```bash
curl --location --request POST 'https://api.dify.ai/v1/datasets/{dataset_id}/documents/{document_id}/segments' \
--header 'Authorization: Bearer {api_key}' \
--header 'Content-Type: application/json' \
--data-raw '{"segments": [{"content": "1","answer": "1","keywords": ["a"]}]}'
```

#### 查询文档分段

```bash
curl --location --request GET 'https://api.dify.ai/v1/datasets/{dataset_id}/documents/{document_id}/segments' \
--header 'Authorization: Bearer {api_key}' \
--header 'Content-Type: application/json'
```

#### 删除文档分段

```bash
curl --location --request DELETE 'https://api.dify.ai/v1/datasets/{dataset_id}/documents/{document_id}/segments/{segment_id}' \
--header 'Authorization: Bearer {api_key}' \
--header 'Content-Type: application/json'
```

#### 更新文档分段

```bash
curl --location --request POST 'https://api.dify.ai/v1/datasets/{dataset_id}/documents/{document_id}/segments/{segment_id}' \
--header 'Authorization: Bearer {api_key}' \
--header 'Content-Type: application/json'\
--data-raw '{"segment": {"content": "1","answer": "1", "keywords": ["a"], "enabled": false}}'
```

### 错误信息

| 错误信息 | 错误码 | 原因描述 |
| --- | --- | --- |
| no_file_uploaded | 400 | 请上传你的文件 |
| too_many_files | 400 | 只允许上传一个文件 |
| file_too_large | 413 | 文件大小超出限制 |
| unsupported_file_type | 415 | 不支持的文件类型。目前只支持以下内容格式：`txt`, `markdown`, `md`, `pdf`, `html`, `html`, `xlsx`, `docx`, `csv` |
| high_quality_dataset_only | 400 | 当前操作仅支持"高质量"知识库 |
| dataset_not_initialized | 400 | 知识库仍在初始化或索引中。请稍候 |
| archived_document_immutable | 403 | 归档文档不可编辑 |
| dataset_name_duplicate | 409 | 知识库名称已存在，请修改你的知识库名称 |
| invalid_action | 400 | 无效操作 |
| document_already_finished | 400 | 文档已处理完成。请刷新页面或查看文档详情 |
| document_indexing | 400 | 文档正在处理中，无法编辑 |
| invalid_metadata | 400 | 元数据内容不正确。请检查并验证 |

## Dify 配置与优化

### 获取高德地图应用Key

1. 访问[高德地图API官网](https://lbs.amap.com/api/webservice/guide/create-key)获取个人Key
2. 个人Key示例：`61ded56e661c7338f95ccafd0c4642d5`
3. MCP服务地址：`https://mcp.amap.com/mcp?=61ded56e661c7338f95ccafd0c4642d5`

### Dify 插件安装

在插件市场安装以下插件：
- Dify Agent策略
- MCP SSE / StreamableHTTP
- MCP server
- MCP Compatible Dify Tools
- 对话Agent
- Agent策略（支持MCP工具）
- MCP Agent策略

### 大模型配置

- 使用SiliconFlow模型
- 项目专用ApiKey：`sk-opwwgzubneoipbdnaejkfcrqrahmyhasefpymcwvkxpnlfbr`
- 在个人页面的`模型供应商`中配置

### MCP调用配置

```json
{
  "server_name":{
    "url":"https://mcp.amap.com/sse?key=61ded56e661c7338f95ccafd0c4642d5",
    "headers":{},
    "timeout":60,
    "sse_read_timeout":300
  }
}
```

### 本地文件挂载

Docker部署的Dify无法直接读取本地文件，需要通过挂载卷解决：

1. 修改`dify/docker/docker-compose.yaml`文件，在sandbox服务中添加挂载：
```yaml
volumes:
      - ./volumes/sandbox/dependencies:/dependencies
      - ./volumes/sandbox/conf:/conf
      - D:\\SourceTree\\front\\Files\\Database:/var/sandbox/sandbox-python
```

2. 在`dify/docker/volumes/sandbox/conf`文件夹下，修改`config.yaml`文件，在`allowed_syscalls`下添加权限

3. 重启Dify容器

### 图片外网访问配置

1. 修改`.env`文件：
```
CONSOLE_WEB_URL=http://103.40.13.100:23452
FILES_URL=http://103.40.13.100:23452
INTERNAL_FILES_URL=
```

2. 修改`docker-compose.yaml`文件，在api服务中添加端口映射：
```yaml
services:
  api:
    image: langgenius/dify-api:1.9.1
    ports:
      - "23452:5001" # 新增5001端口作为图片传输显示端口
```

3. 重新删除文档并上传，确保图片URL更新为外网地址

### 知识库排队问题解决

如果知识库一直显示"排队中"，可能是解析进程阻塞：

1. 检查Docker服务状态：
```bash
cd /home/dify-1.9.1/docker
docker-compose ps
```

2. 检查Worker服务日志：
```bash
docker-compose logs -f worker
```

3. 检查队列中的任务数量：
```bash
docker-compose exec redis redis-cli -n 1 llen dataset
```

4. 检查Celery Worker状态：
```bash
docker-compose exec worker celery -A app.celery inspect stats
```

5. 检查当前正在执行的任务：
```bash
docker-compose exec worker celery -A app.celery inspect active
```

6. 解决方案：增加Worker进程数，在`.env`文件中设置：
```
CELERY_WORKER_AMOUNT=4
```

然后重启Dify服务。