# 初步流程
## 获取高德地图应用Key:
[教程链接:Dify + 高德地图MCP Server，解锁智能生活新姿势！](https://lbs.amap.com/api/webservice/guide/create-key)
- 个人key:`61ded56e661c7338f95ccafd0c4642d5`
https://mcp.amap.com/mcp?=61ded56e661c7338f95ccafd0c4642d5
## Dify 安装插件:
1. 插件市场安装以下插件：
   - Dify Agent策略
   - MCP SSE / StreamableHTTP
   - MCP server
   - MCP Compatible Dify Tools
   - 对话Agent
   - Agent策略（支持MCP工具）
   - MCP Agent策略
- MCP插件使Dify能够接入并调用MCP Server提供的各种服务，例如高德地图的路径规划、天气查询等。
1. 大模型插件
- 目前使用的是SiliconFlow; 项目专用ApiKey为：sk-opwwgzubneoipbdnaejkfcrqrahmyhasefpymcwvkxpnlfbr
- 有点贵的，省着点花
- 下载完后在个人页面的`模型供应商`中使用;
  
1. MCP调用
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


##  挂载本地文件
- docker部署的DIfy无法读取本地文件, 是dify中sandbox问题。https://github.com/langgenius/dify-sandbox/blob/main/FAQ.md
其中一句话挺重要：“dify-sandbox实现会在目录中生成一个临时文件/var/sandbox/sandbox-python/来保存和执行 Python 代码。”
那就挂载卷。修改dify\docker下docker-compose.yaml文件：
找到sandbox服务，添加挂载：
```yaml
volumes:
      - ./volumes/sandbox/dependencies:/dependencies
      - ./volumes/sandbox/conf:/conf
      - D:\\SourceTree\\front\\Files\\Database:/var/sandbox/sandbox-python
```
- 在DIfy的代码执行输入：
```sh
import os
def main() -> dict:
    arg1 = f"current dictionary file: {os.listdir()}"
    return {
        "result": arg1,
    }
```
即可浏览挂载的文件内容；但还是不能查询数据库：
- "operation not permitted"，sandbox做了若干限制。根据官方文档，需要添加权限。在dify\docker\volumes\sandbox\conf文件夹下，修改config.yaml文件，在allowed_syscalls下添加权限;文件很长，已经放到Files\Dify_Database\Dify_Config\config.yaml中，直接复制粘贴即可；

然后重启DIfy容器，即可完成本地文件的修改和读取操作；


# 图片外网访问内网：
## .env
- 图片外网访问内网：
```
CONSOLE_WEB_URL=http://103.40.13.100:23452
FILES_URL=http://103.40.13.100:23452
INTERNAL_FILES_URL=

```
## docker-compose.yaml
- 图片外网访问内网：
```yaml
services:
  # API service
  api:
    image: langgenius/dify-api:1.9.1
    ports:
      - "23452:5001" # 新增5001端口作为图片传输显示端口
```

### 一定一定要记得：重新删除文档，然后上传；以为一旦解析后图片的url就会改变，之前的url依旧是内网的；



# DIfy知识库一直排队中问题；
肯定是解析进程阻塞了；
1. 检查Docker服务状态
  cd /home/dify-1.9.1/docker
  docker-compose ps

2. 检查Worker服务日志
  docker-compose logs -f worker
  
3. 检查队列中的任务数量（关键，大部分都是这里出问题）
  docker-compose exec redis redis-cli -n 1 llen dataset
可以查看到队列中是否有任务在等待处理；我这里有6878个；因为我配置了Dify数据库的自动上传，导致阻塞；

4. 检查Celery Worker状态
docker-compose exec worker celery -A app.celery inspect stats

这个命令显示Worker的详细统计信息，我发现：
- 只有1个worker进程在运行（ pool: gevent TaskPool (max-concurrency=1) ）
- 虽然已经处理了大量任务，但处理速度跟不上任务产生速度

5. 检查当前正在执行的任务
docker-compose exec worker celery -A app.celery inspect active
这个命令显示当前只有1个任务正在执行，进一步确认了worker进程数不足的问题。

6. 检查环境配置文件
看一下.env,其中有几个配置：
```
- CELERY_WORKER_AMOUNT=  #为空
- CELERY_AUTO_SCALE=false  #未启用自动扩展
```
所以：
Celery worker进程数不足，导致任务处理速度跟不上任务产生速度，造成大量任务在队列中积压 。

解决方案：
1. 
- 
```
CELERY_WORKER_AMOUNT=4
```