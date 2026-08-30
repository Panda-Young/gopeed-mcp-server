# Gopeed MCP Server

一个基于 [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) 的 Server，让你能在 VS Code Copilot Chat 中通过自然语言控制 [Gopeed](https://github.com/GopeedLab/gopeed) 下载管理器。

## 功能介绍

本 MCP Server 封装了 Gopeed 的 REST API，提供以下 8 个工具：

| 工具 | 说明 |
|------|------|
| `create_download_task` | 创建下载任务，支持自定义文件名和并发连接数 |
| `list_tasks` | 列出所有下载任务，可按状态过滤 |
| `get_task_detail` | 获取单个任务的详细信息 |
| `pause_task` | 暂停指定任务 |
| `resume_task` | 恢复（继续）指定任务 |
| `delete_task` | 删除任务，可选同时删除已下载文件 |
| `get_config` | 获取 Gopeed 当前配置（下载目录、连接数、代理等） |
| `update_config` | 更新 Gopeed 配置（只传需要修改的字段） |

## 环境要求

- Python 3.10+
- Gopeed 已安装并运行（API 端口每次启动随机分配，无需手动指定）
- VS Code 安装了 GitHub Copilot Chat 扩展

## 安装步骤

1. 进入项目目录：
   ```bash
   cd gopeed-mcp-server
   ```

2. （推荐）创建虚拟环境：
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS / Linux
   source .venv/bin/activate
   ```

3. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

4. （可选）配置环境变量。复制 `.env.example` 为 `.env` 并按需修改：
   ```bash
   copy .env.example .env
   ```
   可用环境变量：
   - `GOPEED_API_URL`：Gopeed API 地址。**推荐留空端口**（默认 `http://127.0.0.1/api/v1`），server 会自动发现 Gopeed 当前端口（Gopeed 每次重启都会随机换端口，自动发现可免去手动改配置）。仅在确需固定时才写 `http://127.0.0.1:<端口>/api/v1`
   - `GOPEED_API_TOKEN`：API 令牌（可选，Gopeed 配置了令牌时需要）
   - `GOPEED_TIMEOUT`：请求超时秒数，默认 `10`

## VS Code Copilot Chat 配置方法

1. 打开 VS Code，按 `Ctrl+Shift+P`（macOS 为 `Cmd+Shift+P`），输入并选择 **"Preferences: Open User Settings (JSON)"**。

2. 在 `settings.json` 中添加 `mcpServers` 配置：

   ```json
   "mcpServers": {
     "gopeed": {
       "command": "C:\\path\\to\\gopeed-mcp-server\\.venv\\Scripts\\python.exe",
       "args": [
         "C:\\path\\to\\gopeed-mcp-server\\server.py"
       ],
       "env": {
         "GOPEED_API_URL": "http://127.0.0.1/api/v1"
       }
     }
   }
   ```

   > **注意**：
   > - `command` 使用虚拟环境中 Python 的**绝对路径**（`<仓库>/.venv/Scripts/python.exe`），避免系统 PATH 中没有 `python` 导致启动失败。
   > - `args` 中的路径需要使用双反斜杠 `\\` 转义，或使用正斜杠 `/`。
   > - `GOPEED_API_URL` 推荐留空端口（`http://127.0.0.1/api/v1`），server 会自动发现 Gopeed 当前监听端口；若已固定端口则写完整地址。
   > - 如果 Gopeed 配置了 API 令牌，在 `env` 中添加 `"GOPEED_API_TOKEN": "你的令牌"`。

3. 保存 `settings.json`，重启 VS Code。

4. 验证配置：打开 Copilot Chat，输入 `@gopeed` 或直接描述需求，Copilot 应能识别并调用 Gopeed 工具。也可以在 VS Code 的 MCP 面板中查看 `gopeed` server 是否处于运行状态。

## 使用示例

在 VS Code Copilot Chat 中，你可以这样说：

| 你说的话 | 触发的操作 |
|----------|-----------|
| "帮我下载这个文件：https://example.com/file.zip" | 创建下载任务 |
| "下载 https://example.com/video.mp4，文件名改成我的视频.mp4，用 32 个连接" | 创建任务并指定文件名和并发数 |
| "看看现在有哪些下载任务" | 列出所有任务 |
| "显示正在下载的任务" | 按 running 状态过滤任务列表 |
| "查看任务 abc123 的详细信息" | 获取任务详情 |
| "暂停任务 abc123" | 暂停任务 |
| "继续任务 abc123" | 恢复任务 |
| "删除任务 abc123" | 删除任务（保留文件） |
| "删除任务 abc123，连文件一起删掉" | 强制删除任务和文件 |
| "Gopeed 当前配置是什么？" | 获取配置 |
| "把并发连接数改成 32" | 更新配置 |
| "把下载目录改成 D:\\Downloads" | 更新下载目录 |
| "启用代理" / "关闭代理" | 更新代理开关 |

## 项目结构

```
gopeed-mcp-server/
├── server.py              # MCP Server 主入口，定义所有 MCP Tools
├── gopeed_client.py       # Gopeed REST API 客户端封装
├── config.py              # 配置管理（从环境变量读取）
├── requirements.txt       # Python 依赖
├── .env.example           # 环境变量示例
└── README.md              # 本文件
```

## 故障排查

### 1. Copilot Chat 无法调用 Gopeed 工具

- 确认 `settings.json` 中 `mcpServers.gopeed` 配置的路径正确，使用双反斜杠 `\\`。
- 确认 `command` 指向虚拟环境中 Python 的**绝对路径**（如 `...\.venv\Scripts\python.exe`），而非裸 `python`（系统 PATH 可能无 `python`）。
- 重启 VS Code 后再试。
- 在 VS Code 中打开 **Output** 面板，选择 **MCP** 通道查看 gopeed server 的日志输出。

### 2. 提示"无法连接到 Gopeed"

- 确认 Gopeed 已启动并正在运行。
- Gopeed 每次重启会随机分配 API 端口，本 server 默认**自动发现**当前端口；若 `GOPEED_API_URL` 写死了旧端口会失效，建议改为留空端口的 `http://127.0.0.1/api/v1`。
- 检查防火墙是否阻止了本地回环连接；若系统启用了代理，localhost 请求可能被拦截返回 503，本 server 已对本地请求禁用代理。

### 3. 提示"Gopeed 业务错误"或"HTTP 401/403"

- Gopeed 可能配置了 API 访问令牌，需要在 `env` 中设置 `GOPEED_API_TOKEN`。
- 在 Gopeed Web UI 的设置中查看是否启用了令牌认证。

### 4. Python 依赖安装失败

- 确保 Python 版本 >= 3.10：`python --version`
- 升级 pip：`pip install --upgrade pip`
- 使用国内镜像源：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`

### 5. 手动测试 Gopeed API 连通性

Gopeed 端口随机，先找到当前端口再用 curl 测试：

```bash
# Windows：通过 netstat 找到 gopeed 监听的回环端口
netstat -ano | findstr "LISTENING" | findstr "gopeed"

# 假设查到端口为 12345，则：
curl http://127.0.0.1:12345/api/v1/config
curl http://127.0.0.1:12345/api/v1/tasks
```

如果 curl 能正常返回 JSON 数据（含 `"code":0`），说明 Gopeed API 正常，问题出在 MCP Server 配置或 Python 环境。

## 许可证

MIT
