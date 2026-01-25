## 代码文件path：
 - home/effect/calculator/bridge/bridge_api_v0.py
 - 
# 启动
nohup python3 bridge_api_v0.py &
nohup python3 home/effect/calculator/bridge/bridge_api_v0.py &

# 查看进程
ps aux | grep bridge_api_v0.py
ps aux | grep home/effect/calculator/bridge/bridge_api_v0.py
# 停止
kill xxxx(pid)

# 查看python3版本
python3 --version

# 查看路径
which python3

# Dify：
```
url: http://emocat365.top:23452/apps
account：admin
password：admin


Ollama:
snap set ollama host=0.0.0.0
snap restart ollama
```

---

# 定时任务设置教程 (Cron Job Setup)

本教程将指导您如何设置 Linux Crontab 定时任务，以便每隔 30 分钟自动运行一次爬虫脚本。

## 1. 准备工作

在设置定时任务之前，请确保您知道以下两个路径：

1.  **Python 解释器路径**:
    在终端运行以下命令获取：
    ```bash
    which python3
    ```
    *假设输出为*: `/usr/bin/python3`

2.  **脚本入口文件路径**:
    即 `main.py` 的绝对路径。
    *假设您的脚本位于*: `/home/project1/Files/Spider/main.py`

## 2. 编写定时任务

### 步骤 1: 打开 Crontab 编辑器

在终端输入以下命令：
```bash
crontab -e
```
如果是第一次运行，系统可能会询问您选择编辑器（如 nano 或 vim）。
- 选择 `nano`（通常是选项 1）比较容易上手。

### 步骤 2: 添加任务规则

在打开的文件末尾，添加以下一行内容：

```bash
*/30 * * * * /usr/bin/python3 /home/project1/Files/Spider/main.py >> /home/project1/Files/Spider/spider.log 2>&1
```

**详细解释：**
- `*/30 * * * *`: Cron 表达式，表示"每隔 30 分钟执行一次"。
- `/usr/bin/python3`: **[重要]** 请替换为您在"准备工作"中获取的 Python 解释器绝对路径。
- `/home/project1/Files/Spider/main.py`: **[重要]** 请替换为您的脚本绝对路径。
- `>> /home/project1/Files/Spider/spider.log`: 将标准输出（stdout）追加写入到日志文件 `spider.log` 中，方便排查问题。
- `2>&1`: 将错误输出（stderr）也重定向到标准输出，这样错误信息也会记录在日志里。

### 步骤 3: 保存并退出

- **如果您使用的是 nano 编辑器**:
  1. 按 `Ctrl + O` 保存。
  2. 按 `Enter` 确认文件名。
  3. 按 `Ctrl + X` 退出。

- **如果您使用的是 vim 编辑器**:
  1. 按 `Esc` 键。
  2. 输入 `:wq`。
  3. 按 `Enter`。

## 3. 验证任务

设置完成后，您可以使用以下命令查看当前用户的定时任务列表，确认是否添加成功：

```bash
crontab -l
```

如果看到刚才添加的那一行，说明设置成功。

## 4. 监控运行

您可以随时查看日志文件来确认脚本是否正常运行：

```bash
tail -f /home/project1/Files/Spider/spider.log
```

---

## 常见问题排查

1.  **路径问题**: Cron 任务在一个最小化的环境中运行，**不会自动加载用户的环境变量**。因此，务必使用**绝对路径**来指定 python 和脚本文件。
2.  **依赖问题**: 如果脚本依赖于特定的 Python 虚拟环境，请使用虚拟环境中的 python 可执行文件路径（例如 `/home/user/myenv/bin/python`）代替 `/usr/bin/python3`。
3.  **权限问题**: 确保您的脚本文件具有执行权限，且日志文件的目录可写。
