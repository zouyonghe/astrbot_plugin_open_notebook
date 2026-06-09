# AstrBot Open Notebook 插件

把 [Open Notebook](https://github.com/lfnovo/open-notebook) 接入 AstrBot。你可以在 IM 聊天里创建 notebook、切换当前 notebook、上传文档并查询内容，也可以让 AstrBot Agent 通过 LLM 工具调用同一套能力。

## 功能

- 在聊天中管理 Open Notebook notebooks。
- 将聊天上传或引用的文件加入 notebook。
- 自动选择唯一 notebook；没有 notebook 时可自动创建。
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
| `astrbot_provider_id` | 要同步到 Open Notebook 的 AstrBot 模型 ID。留空时使用当前会话正在使用的 chat 模型 | 空 |
| `open_notebook_model_provider` | Open Notebook provider 覆盖值，例如 `openai_compatible`。留空自动推断 | 空 |
| `auto_sync_astrbot_chat_model` | 查询前自动同步 AstrBot chat 模型。会把 API Key 写入 Open Notebook | `false` |

Open Notebook REST API 默认运行在 `http://localhost:5055`。如果 AstrBot 和 Open Notebook 不在同一台机器，请把 `base_url` 改成 AstrBot 服务器可访问的地址。

## 命令

命令前缀是 `/on`。

```text
/on ls
/on create <名称> [描述]
/on use <notebook名称或ID>
/on current
/on upload
/on sync-model
/on ask <问题>
/on delete <notebook名称或ID>
/on help
```

`/on use` 和 `/on delete` 支持列表序号，例如 `/on use 1`。`/on upload` 会读取当前消息或引用消息中的文件：如果没有 notebook，会按文件名自动创建；如果只有一个 notebook，会直接使用；如果有多个 notebook 且当前会话未选择，会提示先切换。

如果 Open Notebook 没有默认 chat 模型，可以使用 `/on sync-model`。插件会读取配置中的 `astrbot_provider_id`，或当前会话正在使用的 AstrBot chat 模型，把它同步为 Open Notebook 的默认 chat 模型。同步会创建或更新 Open Notebook credential、model，并设置 `default_chat_model`。

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
- `open_notebook_sync_astrbot_model`

`open_notebook_upload_file` 支持可选 `notebook` 参数。Agent 可以传入 notebook ID、名称、序号，或一个新名称；如果目标不存在，插件会自动创建后上传。未传入时会优先使用当前会话 notebook，其次自动使用唯一 notebook；多个 notebook 时会使用列表中的第一个 notebook，Agent 也可以先调用列表工具后自行选择目标。

`open_notebook_sync_astrbot_model` 可以让 Agent 主动把当前 AstrBot chat 模型同步为 Open Notebook 默认 chat 模型。

如果 `admin_only` 开启，LLM 工具和聊天命令都会要求调用者是 AstrBot 管理员。

## 依赖

插件依赖 `httpx`，AstrBot 安装插件时会读取 `requirements.txt`。

---

# AstrBot Open Notebook Plugin

This plugin connects [Open Notebook](https://github.com/lfnovo/open-notebook) to AstrBot. You can create notebooks, switch the current notebook, upload documents from chat, and ask questions from IM. AstrBot Agents can also call the same features through LLM tools.

## Features

- Manage Open Notebook notebooks from chat.
- Upload current or quoted chat files into notebooks.
- Automatically use the only notebook, or create one when none exists.
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
| `astrbot_provider_id` | AstrBot model provider ID to sync into Open Notebook. Empty means current chat provider | empty |
| `open_notebook_model_provider` | Override Open Notebook provider, such as `openai_compatible`. Empty means auto-detect | empty |
| `auto_sync_astrbot_chat_model` | Sync AstrBot chat model before queries. This writes the API key into Open Notebook | `false` |

Open Notebook's REST API runs on `http://localhost:5055` by default. If AstrBot and Open Notebook run on different hosts, set `base_url` to an address reachable from the AstrBot server.

## Commands

The command prefix is `/on`.

```text
/on ls
/on create <name> [description]
/on use <notebook name or id>
/on current
/on upload
/on sync-model
/on ask <question>
/on delete <notebook name or id>
/on help
```

`/on use` and `/on delete` accept list indexes, for example `/on use 1`. `/on upload` reads the file attached to the current message or quoted message. If no notebook exists, it creates one from the file name. If exactly one notebook exists, it uses it automatically. If multiple notebooks exist and the chat session has no current notebook, it asks you to switch first.

If Open Notebook has no default chat model, run `/on sync-model`. The plugin reads `astrbot_provider_id`, or the current AstrBot chat provider, and syncs it into Open Notebook as the default chat model by creating or updating the credential, model, and `default_chat_model` setting.

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
- `open_notebook_sync_astrbot_model`

`open_notebook_upload_file` accepts an optional `notebook` argument. Agents can pass a notebook ID, name, list index, or a new name; missing targets are created automatically before upload. Without a target, the tool uses the current session notebook, then the only existing notebook, and finally the first notebook when multiple exist.

`open_notebook_sync_astrbot_model` lets the Agent sync the current AstrBot chat model into Open Notebook as the default chat model.

When `admin_only` is enabled, both commands and LLM tools require an AstrBot admin caller.
