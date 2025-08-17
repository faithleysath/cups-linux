# 轻量级云打印系统 (CUPS Web Print)

这是一个轻量级的云打印解决方案，允许用户通过 Web 界面上传文件并将其发送到连接到 Linux 服务器的 CUPS 打印机，而无需在客户端安装任何驱动程序。

## 特性

- **Web 界面上传**: 简洁的前端页面，支持文件上传。
- **动态打印机列表**: 自动从 CUPS 读取并显示可用的打印机。
- **通用格式支持**: 自动将 Word (`.doc`, `.docx`) 和图片 (`.jpg`, `.png`) 文件转换为打印机可识别的 PDF 格式。
- **打印参数设置**: 支持设置打印份数。
- **实时状态反馈**: 提交打印后，前端会轮询并显示打印任务的状态。
- **无客户端驱动**: 所有打印处理均在服务器端完成。

## 技术栈

- **后端**: Python (Flask) + pycups
- **前端**: 原生 HTML, CSS, JavaScript
- **文件转换**: LibreOffice (用于 Office 文档), Pillow (用于图片)

## 部署要求

在部署此应用前，请确保您的 Linux 服务器满足以下条件：

1.  **已安装并配置 CUPS**: 打印机必须已在 CUPS 中成功安装和配置，并可以正常打印测试页。
2.  **Python 3.x 环境**: 需要 Python 3.6 或更高版本。
3.  **LibreOffice**: 用于将 Word 文档转换为 PDF。
    - 在 Debian/Ubuntu 上安装: `sudo apt-get update && sudo apt-get install -y libreoffice`
4.  **CUPS 开发库**: `pycups` 库需要 `libcups2-dev`。
    - 在 Debian/Ubuntu 上安装: `sudo apt-get install -y libcups2-dev`
5.  **网络访问**: 服务器的 5000 端口（或您配置的其他端口）需要对局域网内的用户开放。

## 安装与运行

1.  **克隆或下载项目**
    将本项目文件放置在服务器的任意目录，例如 `/opt/cups-print-system`。

2.  **创建并激活 Python 虚拟环境**
    ```bash
    cd /path/to/cups-print-system
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **安装依赖项**
    ```bash
    pip install -r requirements.txt
    ```

4.  **运行应用**
    ```bash
    python app.py
    ```
    应用默认将在 `0.0.0.0:5000` 上运行。您现在可以通过浏览器访问 `http://<服务器IP地址>:5000` 来使用云打印服务。

## 生产环境部署 (可选)

为了在生产环境中更稳定地运行，建议使用 Gunicorn 或 uWSGI 等 WSGI 服务器，并使用 Nginx 作为反向代理。

**使用 Gunicorn 运行:**
```bash
# 安装 gunicorn
pip install gunicorn

# 运行 (假设有 4 个 CPU 核心)
gunicorn --workers 4 --bind 0.0.0.0:5000 app:app
```

## 工作流程

1.  **文件上传**: 用户在 Web 页面选择文件、打印机和份数。
2.  **后端接收**: Flask 后端接收文件并将其保存到 `uploads/` 临时目录。
3.  **格式转换**:
    - 如果文件是 `.doc` 或 `.docx`，系统调用 `libreoffice` 将其转换为 PDF。
    - 如果是图片，系统使用 `Pillow` 库将其转换为 PDF。
    - 如果已经是 PDF，则跳过此步骤。
4.  **提交打印**: 后端使用 `pycups` 库将转换后的 PDF 文件提交到用户选择的 CUPS 打印机队列。
5.  **状态反馈**: 前端获取任务 ID 后，会定期向后端查询该任务的状态，并将结果（如 `processing`, `completed`, `error`）显示给用户。

## 注意事项

- **文件权限**: 确保运行应用的用户对 `uploads/` 目录有读写权限。
- **安全性**: 此应用设计为在受信任的内部网络（如家庭或办公室局域网）中使用，因为它没有用户认证机制。请勿将其直接暴露在公共互联网上。
- **CUPS 权限**: 运行此应用的用户需要有权限连接到 CUPS 并提交打印任务。通常，将该用户添加到 `lpadmin` 组可以解决权限问题 (`sudo usermod -a -G lpadmin <username>`)。
