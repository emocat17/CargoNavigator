# 抓取高速路况,施工信息,保存为md

`https://www.fjetc.com/traffic-info`
~~https://qz.bendibao.com/mtools/gaosu/~~

## 先运行extract_event_details.py, 提取事件代码和url;  
 - (可选) 手动检查提取结果, 可测试单个文件提取extract_event_details.py,运行确认无误后, 继续下一步;
## 再运行batch_extract_event_details.py, 批量提取事件详情;

这个错误是因为DrissionPage在您的Linux系统上找不到Chrome浏览器。下面我为您整理了解决方案。

### 🔍 问题根源

错误信息 `FileNotFoundError: [Errno 2] No such file or directory: 'chrome'` 表明，DrissionPage尝试自动启动名为 `chrome` 的可执行文件，但在系统的环境变量 `PATH` 所包含的目录里没有找到它。



#### 安装Chrome浏览器（如果未安装）

如果系统尚未安装Chrome，您需要先安装它。

1.  **更新软件包列表**：
    ```bash
    sudo apt update
    ```
2.  **安装Chrome**：
    您可以去[Google Chrome官网](https://www.google.com/chrome/)下载`.deb`包安装，或者使用以下命令通过Wget安装：
    ```bash
    wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
    sudo apt install ./google-chrome-stable_current_amd64.deb
    ```
3.  **验证安装**：
    安装完成后，可以在终端输入 `which google-chrome` 来检查Chrome的安装路径。通常它会位于 `/usr/bin/google-chrome`。

4. **安装playwright浏览器驱动**：
    ```bash
    playwright install
    ```

