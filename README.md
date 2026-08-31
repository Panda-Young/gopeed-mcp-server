# Gopeed MCP Server

一个基于 [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) 的 Server，让你能在各种 AI Agent / 智能体中通过自然语言控制 [Gopeed](https://github.com/GopeedLab/gopeed) 下载管理器。它遵循标准 MCP 协议，可无缝接入任意兼容 MCP 的客户端，例如 VS Code Copilot Chat、WorkBuddy、Trae 等。

> **关于 Gopeed**：本项目的被控对象是开源下载管理器 [Gopeed](https://github.com/GopeedLab/gopeed)（由 `GopeedLab` 维护，采用 [GPL-3.0](https://github.com/GopeedLab/gopeed/blob/main/LICENSE) 许可证）。本 Server 仅通过 Gopeed 公开的 **REST API** 与之通信，不修改、不嵌入其任何源代码，因此本仓库以 MIT 许可证独立发布。使用前请先安装并运行 Gopeed 本体。

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
- 任意兼容 MCP 的 AI Agent / 智能体客户端（如 VS Code Copilot Chat、WorkBuddy、Trae 等）

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

3. 安装依赖（二选一）：

   - 方式 A：从源码安装依赖
     ```bash
     pip install -r requirements.txt
     ```

   - 方式 B：作为 Python 包安装（推荐，可用于 `uvx` 一键启动）
     ```bash
     pip install .
     # 或发布后： pip install gopeed-mcp-server
     ```
     安装后会得到 `gopeed-mcp-server` 命令，可用 `uvx gopeed-mcp-server` 直接启动。

4. （可选）配置环境变量。复制 `.env.example` 为 `.env` 并按需修改：
   ```bash
   copy .env.example .env
   ```
   可用环境变量：
   - `GOPEED_API_URL`：Gopeed API 地址。**推荐留空端口**（默认 `http://127.0.0.1/api/v1`），server 会自动发现 Gopeed 当前端口（Gopeed 每次重启都会随机换端口，自动发现可免去手动改配置）。仅在确需固定时才写 `http://127.0.0.1:<端口>/api/v1`
   - `GOPEED_API_TOKEN`：API 令牌（可选，Gopeed 配置了令牌时需要）
   - `GOPEED_TIMEOUT`：请求超时秒数，默认 `10`

## VS Code Copilot Chat 配置方法

**方式一：从 MCP Gallery 安装（推荐，已上架后）**

1. 打开 Extensions 视图（`Ctrl+Shift+X`），搜索 `@mcp gopeed`。
2. 选择 **Install** 安装到用户配置，按提示信任并启动即可。

**方式二：手动配置 `mcp.json`**

VS Code 1.99+ 使用专用的 `mcp.json`（而不是 `settings.json` 的 `mcpServers` 字段）。

1. 按 `Ctrl+Shift+P`，运行 **`MCP: Open User Configuration`**（或在工作区创建 `.vscode/mcp.json`）。
2. 添加如下配置（使用 `uvx` 启动，无需本地路径）：

   ```json
   {
     "servers": {
       "gopeed": {
         "command": "uvx",
         "args": ["gopeed-mcp-server"],
         "env": {
           "GOPEED_API_URL": "http://127.0.0.1/api/v1"
         }
       }
     }
   }
   ```

   若未发布到 PyPI，可改用本地源码方式：

   ```json
   {
     "servers": {
       "gopeed": {
         "command": "python",
         "args": ["<仓库绝对路径>/server.py"],
         "env": {
           "GOPEED_API_URL": "http://127.0.0.1/api/v1"
         }
       }
     }
   }
   ```

   > **注意**：
   > - `GOPEED_API_URL` 推荐留空端口（`http://127.0.0.1/api/v1`），server 会自动发现 Gopeed 当前监听端口；若已固定端口则写完整地址。
   > - 如果 Gopeed 配置了 API 令牌，在 `env` 中添加 `"GOPEED_API_TOKEN": "你的令牌"`。
   > - Windows 沙箱（sandbox）目前不可用，本地 stdio server 直接运行。

3. 保存 `mcp.json`，重启 VS Code（或 `Developer: Reload Window`）。

4. 验证配置：打开 Copilot Chat，输入 `@gopeed` 或直接描述需求，Copilot 应能识别并调用 Gopeed 工具。也可在 MCP 面板中查看 `gopeed` server 状态。

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
├── pyproject.toml         # 打包配置（提供 gopeed-mcp-server 命令）
├── requirements.txt       # Python 依赖
├── .env.example           # 环境变量示例
├── icon.png               # MCP Gallery 图标
└── README.md              # 本文件
```

## 故障排查

### 1. Copilot Chat 无法调用 Gopeed 工具

- 确认 `mcp.json` 中 `servers.gopeed` 配置正确（`uvx gopeed-mcp-server` 或本地 `python server.py`），路径使用正斜杠或双反斜杠 `\\`。
- 若使用本地源码方式，确认 `command` 指向可运行的 Python（如 `...\.venv\Scripts\python.exe` 或裸 `python`），而非错误路径。
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

本项目（Gopeed MCP Server）以 **MIT** 许可证发布，详见 [LICENSE](./LICENSE)。

被控对象 [Gopeed](https://github.com/GopeedLab/gopeed) 本身是独立的开源项目，采用 **GPL-3.0** 许可证（© GopeedLab 及其贡献者）。本 Server 仅通过网络调用其公开 REST API 进行集成，不构成对 Gopeed 源代码的修改或衍生，亦不随本仓库分发 Gopeed 的任何代码。如使用 Gopeed 本体，请遵守其对应的许可证条款。

## 发布与上架

本 server 已打包为 Python 包（见 `pyproject.toml`），提供 `gopeed-mcp-server` 命令，可被任何兼容 MCP 的 AI Agent / 智能体客户端、社区 registry 等直接引用。

- **GitHub（已公开）**：仓库即发布页。别人在 GitHub 搜到后，按上面的 `mcp.json` 片段手动添加即可使用。
- **PyPI**：`pip install gopeed-mcp-server` 或直接 `uvx gopeed-mcp-server`（需先发布到 PyPI，见下文）。
- **Glama**：打开 https://glama.ai/mcp/register ，粘贴本仓库 URL（`https://github.com/Panda-Young/gopeed-mcp-server`），会自动读取仓库根的 `mcp.json`。
- **Smithery**：本地 stdio server 用 CLI 发布（非网页表单）。安装 `@smithery/cli` 后，在仓库目录执行 `smithery login` 再 `smithery mcp publish . -n @<你的用户名>/gopeed-mcp-server`（会读取 `smithery.yaml`）。
- **VS Code MCP Gallery**：VS Code 内置的 MCP Gallery 目前为微软托管的精选列表，**没有公开的投稿入口**，个人开发者暂无法直接上架。用户可从上面的 GitHub / PyPI / Glama / Smithery 任一渠道获取并手动配置到 `mcp.json`。
- **手动分享**：任何已安装本包的环境，把上面的 `mcp.json` 片段加入 `mcp.json` 即可使用。

### 发布到 PyPI

```bash
# 本地已构建好 dist/ 下的 wheel 与 sdist
$env:TWINE_USERNAME="__token__"
$env:TWINE_PASSWORD="pypi-你的PyPI令牌"   # 从 https://pypi.org/manage/account/token/ 获取
.venv/Scripts/twine.exe upload dist/*
```
