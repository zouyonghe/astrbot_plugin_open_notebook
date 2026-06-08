# AstrBot Open Notebook 插件

把 [Open Notebook](https://github.com/lfnovo/open-notebook) 接入 AstrBot。你可以在 IM 聊天里创建 notebook、切换当前 notebook、上传文档并查询内容，也可以让 AstrBot Agent 通过 LLM 工具调用同一套能力。

## 功能

- 在聊天中管理 Open Notebook notebooks。
- 将聊天上传的文件加入当前 notebook。
- 基于当前 notebook 提问。
- 提供同等 LLM 工具，方便 Agent 自动调用。
- 支持自定义 Open Notebook API 地址和密码。
- 支持配置是否仅 AstrBot 管理员可用。

## 配置

插件配置均使用中文说明，可在 AstrBot WebUI 插件配置页编辑。

| 配置项 | 说明 | 默认值 |
| --- | --- | --- |
| `base_url` | Open Notebook API 地址，例如 `http://localhost:5055` | `http://localhost:5055` |
| `api_password` | Open Notebook API 密码。若未启用 `OPEN_NOTEBOOK_PASSWORD`，留空即可 | 空 |
| `admin_only` | 是否仅允许 AstrBot 管理员使用命令和工具 | `true` |
| `embed_on_upload` | 上传后是否生成向量索引 | `true` |
| `async_processing` | 上传后是否异步处理文档 | `true` |

Open Notebook REST API 默认运行在 `http://localhost:5055`。如果 AstrBot 和 Open Notebook 不在同一台机器，请把 `base_url` 改成 AstrBot 服务器可访问的地址。

## 命令

命令前缀是 `/on`。

```text
/on ls
/on create <名称> [描述]
/on use <notebook名称或ID>
/on current
/on upload
/on ask <问题>
/on delete <notebook名称或ID>
```

典型流程：

```text
/on ls
/on create 论文资料
/on use 论文资料
```

然后在聊天里上传一个文件，并在同一条消息里发送：

```text
/on upload
```

上传后查询：

```text
/on ask 这份文档主要讲了什么？
```

## LLM 工具

插件也会注册以下 LLM 工具：

- `open_notebook_list_notebooks`
- `open_notebook_create_notebook`
- `open_notebook_switch_notebook`
- `open_notebook_upload_file`
- `open_notebook_ask`
- `open_notebook_delete_notebook`

如果 `admin_only` 开启，LLM 工具和聊天命令都会要求调用者是 AstrBot 管理员。

## 依赖

插件依赖 `httpx`，AstrBot 安装插件时会读取 `requirements.txt`。

---

# AstrBot Open Notebook Plugin

This plugin connects [Open Notebook](https://github.com/lfnovo/open-notebook) to AstrBot. You can create notebooks, switch the current notebook, upload documents from chat, and ask questions from IM. AstrBot Agents can also call the same features through LLM tools.

## Features

- Manage Open Notebook notebooks from chat.
- Upload chat files into the current notebook.
- Ask questions against the current notebook.
- Expose equivalent LLM tools for Agent automation.
- Configure a custom Open Notebook API base URL and optional password.
- Restrict usage to AstrBot admins if needed.

## Configuration

| Key | Description | Default |
| --- | --- | --- |
| `base_url` | Open Notebook API URL, such as `http://localhost:5055` | `http://localhost:5055` |
| `api_password` | Open Notebook API password. Leave empty if `OPEN_NOTEBOOK_PASSWORD` is not enabled | empty |
| `admin_only` | Restrict commands and tools to AstrBot admins | `true` |
| `embed_on_upload` | Generate vector embeddings after upload | `true` |
| `async_processing` | Process uploaded documents asynchronously | `true` |

Open Notebook's REST API runs on `http://localhost:5055` by default. If AstrBot and Open Notebook run on different hosts, set `base_url` to an address reachable from the AstrBot server.

## Commands

The command prefix is `/on`.

```text
/on ls
/on create <name> [description]
/on use <notebook name or id>
/on current
/on upload
/on ask <question>
/on delete <notebook name or id>
```

Example flow:

```text
/on create Research
/on use Research
/on upload
/on ask What is this document about?
```

## LLM Tools

The plugin registers these LLM tools:

- `open_notebook_list_notebooks`
- `open_notebook_create_notebook`
- `open_notebook_switch_notebook`
- `open_notebook_upload_file`
- `open_notebook_ask`
- `open_notebook_delete_notebook`

When `admin_only` is enabled, both commands and LLM tools require an AstrBot admin caller.
