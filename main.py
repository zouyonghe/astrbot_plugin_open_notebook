from pathlib import Path
from typing import Any

import astrbot.api.message_components as Comp
from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register
from astrbot.core.star.filter.command import GreedyStr
from astrbot.core.utils.astrbot_path import get_astrbot_plugin_data_path

from .open_notebook_client import OpenNotebookClient
from .session_store import SessionStore

PLUGIN_NAME = "astrbot_plugin_open_notebook"


@filter.command_group("on")
def on():
    pass


@register(PLUGIN_NAME, "buding", "Open Notebook integration", "0.1.0")
class OpenNotebookPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        data_dir = Path(get_astrbot_plugin_data_path()) / PLUGIN_NAME
        self.session_store = SessionStore(data_dir / "sessions.json")

    @on.command("ls")
    async def list_notebooks(self, event: AstrMessageEvent):
        """列出 Open Notebook notebooks。"""
        if denied := self._require_permission(event):
            yield event.plain_result(denied)
            return
        try:
            notebooks = await self._client().list_notebooks()
        except Exception as exc:
            logger.error(f"Open Notebook list failed: {exc}")
            yield event.plain_result(f"获取 notebook 列表失败：{exc}")
            return
        yield event.plain_result(self._format_notebooks(notebooks))

    @on.command("help")
    async def help(self, event: AstrMessageEvent):
        """显示 Open Notebook 插件帮助。"""
        yield event.plain_result(self._help_text())

    @on.command("create")
    async def create_notebook(
        self,
        event: AstrMessageEvent,
        name: str,
        description: GreedyStr = "",
    ):
        """创建 Open Notebook notebook。"""
        if denied := self._require_permission(event):
            yield event.plain_result(denied)
            return
        try:
            notebook = await self._client().create_notebook(
                name, str(description or "")
            )
        except Exception as exc:
            logger.error(f"Open Notebook create failed: {exc}")
            yield event.plain_result(f"创建 notebook 失败：{exc}")
            return
        self.session_store.set(
            self._session_id(event),
            str(notebook.get("id", "")),
            str(notebook.get("name", name)),
        )
        yield event.plain_result(
            f"已创建并切换到 notebook：{notebook.get('name', name)}\nID：{notebook.get('id', '')}"
        )

    @on.command("use")
    async def use_notebook(self, event: AstrMessageEvent, notebook: GreedyStr):
        """切换当前聊天会话使用的 notebook。"""
        if denied := self._require_permission(event):
            yield event.plain_result(denied)
            return
        try:
            resolved = await self._find_notebook(str(notebook))
        except Exception as exc:
            yield event.plain_result(f"切换 notebook 失败：{exc}")
            return
        self.session_store.set(
            self._session_id(event),
            str(resolved.get("id", "")),
            str(resolved.get("name", "")),
        )
        yield event.plain_result(
            f"当前会话已切换到 notebook：{resolved.get('name', '')}\nID：{resolved.get('id', '')}"
        )

    @on.command("current")
    async def current_notebook(self, event: AstrMessageEvent):
        """显示当前聊天会话使用的 notebook。"""
        if denied := self._require_permission(event):
            yield event.plain_result(denied)
            return
        current = self._current_notebook(event)
        if not current:
            yield event.plain_result(
                "当前会话还没有选择 notebook，请先使用 /on use <名称或ID>。"
            )
            return
        yield event.plain_result(
            f"当前 notebook：{current['name']}\nID：{current['id']}"
        )

    @on.command("upload")
    async def upload_document(self, event: AstrMessageEvent):
        """上传当前消息中的文件到当前 notebook。"""
        if denied := self._require_permission(event):
            yield event.plain_result(denied)
            return
        try:
            file_path = await self._get_attached_file(event)
        except Exception as exc:
            yield event.plain_result(str(exc))
            return
        try:
            current = await self._notebook_for_upload(
                event, file_path, allow_multi_auto=False
            )
        except ValueError as exc:
            yield event.plain_result(str(exc))
            return
        try:
            source = await self._client().upload_file(
                current["id"],
                file_path,
                title=None,
                embed=bool(self.config.get("embed_on_upload", True)),
                async_processing=bool(self.config.get("async_processing", True)),
            )
        except Exception as exc:
            logger.error(f"Open Notebook upload failed: {exc}")
            yield event.plain_result(f"上传文档失败：{exc}")
            return
        yield event.plain_result(
            f"文档已提交到 notebook：{current['name']}\nSource ID：{source.get('id', '')}"
        )

    @on.command("ask")
    async def ask_notebook(self, event: AstrMessageEvent, question: GreedyStr):
        """向当前 notebook 提问。"""
        if denied := self._require_permission(event):
            yield event.plain_result(denied)
            return
        answer = await self._ask_current(event, str(question))
        yield event.plain_result(answer)

    @on.command("delete")
    async def delete_notebook(self, event: AstrMessageEvent, notebook: GreedyStr):
        """删除 Open Notebook notebook。"""
        if denied := self._require_permission(event):
            yield event.plain_result(denied)
            return
        try:
            resolved = await self._find_notebook(str(notebook))
            await self._client().delete_notebook(str(resolved["id"]))
        except Exception as exc:
            logger.error(f"Open Notebook delete failed: {exc}")
            yield event.plain_result(f"删除 notebook 失败：{exc}")
            return
        if (
            self._current_notebook(event)
            and self._current_notebook(event)["id"] == resolved["id"]
        ):
            self.session_store.clear(self._session_id(event))
        yield event.plain_result(f"已删除 notebook：{resolved.get('name', '')}")

    @filter.llm_tool(name="open_notebook_list_notebooks")
    async def tool_list_notebooks(self, event: AstrMessageEvent) -> str:
        """列出 Open Notebook 中的 notebooks。"""
        if denied := self._require_permission(event):
            return denied
        return self._format_notebooks(await self._client().list_notebooks())

    @filter.llm_tool(name="open_notebook_create_notebook")
    async def tool_create_notebook(
        self,
        event: AstrMessageEvent,
        name: str,
        description: str = "",
    ) -> str:
        """创建一个 Open Notebook notebook。

        Args:
            name(string): notebook 名称
            description(string): notebook 描述，可以为空
        """
        if denied := self._require_permission(event):
            return denied
        notebook = await self._client().create_notebook(name, description)
        return f"已创建 notebook：{notebook.get('name', name)}，ID：{notebook.get('id', '')}"

    @filter.llm_tool(name="open_notebook_switch_notebook")
    async def tool_switch_notebook(self, event: AstrMessageEvent, notebook: str) -> str:
        """切换当前聊天会话使用的 Open Notebook notebook。

        Args:
            notebook(string): notebook ID、完整名称或唯一名称片段
        """
        if denied := self._require_permission(event):
            return denied
        resolved = await self._find_notebook(notebook)
        self.session_store.set(
            self._session_id(event),
            str(resolved.get("id", "")),
            str(resolved.get("name", "")),
        )
        return f"当前会话已切换到 notebook：{resolved.get('name', '')}，ID：{resolved.get('id', '')}"

    @filter.llm_tool(name="open_notebook_upload_file")
    async def tool_upload_file(
        self,
        event: AstrMessageEvent,
        file_path: str,
        title: str = "",
        notebook: str = "",
    ) -> str:
        """上传本地文件路径到 Open Notebook notebook。

        Args:
            file_path(string): AstrBot 服务器可访问的本地文件路径
            title(string): source 标题，可以为空
            notebook(string): 目标 notebook 的 ID、名称、序号，或要自动创建的新名称。可以为空
        """
        if denied := self._require_permission(event):
            return denied
        path = Path(file_path)
        current = await self._notebook_for_upload(
            event,
            path,
            notebook_hint=notebook,
            allow_multi_auto=True,
        )
        source = await self._client().upload_file(
            current["id"],
            path,
            title=title or None,
            embed=bool(self.config.get("embed_on_upload", True)),
            async_processing=bool(self.config.get("async_processing", True)),
        )
        return f"文档已提交到 notebook：{current['name']}，Source ID：{source.get('id', '')}"

    @filter.llm_tool(name="open_notebook_ask")
    async def tool_ask(self, event: AstrMessageEvent, question: str) -> str:
        """向当前 Open Notebook notebook 提问。

        Args:
            question(string): 要询问的问题
        """
        if denied := self._require_permission(event):
            return denied
        return await self._ask_current(event, question)

    @filter.llm_tool(name="open_notebook_delete_notebook")
    async def tool_delete_notebook(self, event: AstrMessageEvent, notebook: str) -> str:
        """删除 Open Notebook notebook。

        Args:
            notebook(string): notebook ID、完整名称或唯一名称片段
        """
        if denied := self._require_permission(event):
            return denied
        resolved = await self._find_notebook(notebook)
        await self._client().delete_notebook(str(resolved["id"]))
        if (
            self._current_notebook(event)
            and self._current_notebook(event)["id"] == resolved["id"]
        ):
            self.session_store.clear(self._session_id(event))
        return f"已删除 notebook：{resolved.get('name', '')}"

    def _client(self) -> OpenNotebookClient:
        return OpenNotebookClient(
            str(self.config.get("base_url", "http://localhost:5055")),
            str(self.config.get("api_password", "")),
        )

    def _require_permission(self, event: AstrMessageEvent) -> str | None:
        if bool(self.config.get("admin_only", True)) and event.role != "admin":
            return "权限不足：当前插件配置为仅 AstrBot 管理员可用。"
        return None

    def _session_id(self, event: AstrMessageEvent) -> str:
        return f"{event.get_platform_id()}:{event.get_session_id()}"

    def _current_notebook(self, event: AstrMessageEvent) -> dict[str, str] | None:
        return self.session_store.get(self._session_id(event))

    async def _find_notebook(self, value: str) -> dict[str, Any]:
        query = value.strip()
        if not query:
            raise ValueError("请提供 notebook 名称或 ID。")
        notebooks = await self._client().list_notebooks()
        if query.isdigit():
            index = int(query)
            if 1 <= index <= len(notebooks):
                return notebooks[index - 1]
        for notebook in notebooks:
            if str(notebook.get("id", "")) == query:
                return notebook
        for notebook in notebooks:
            if str(notebook.get("name", "")) == query:
                return notebook
        matches = [
            notebook
            for notebook in notebooks
            if query.lower() in str(notebook.get("name", "")).lower()
        ]
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise ValueError(f"没有找到 notebook：{query}")
        names = "、".join(str(item.get("name", "")) for item in matches[:5])
        raise ValueError(f"匹配到多个 notebook，请使用更精确的名称或 ID：{names}")

    async def _notebook_for_upload(
        self,
        event: AstrMessageEvent,
        file_path: Path,
        *,
        notebook_hint: str = "",
        allow_multi_auto: bool,
    ) -> dict[str, str]:
        hint = notebook_hint.strip()
        if hint:
            try:
                notebook = await self._find_notebook(hint)
            except ValueError:
                notebook = await self._client().create_notebook(hint, "")
            self._set_current_notebook(event, notebook)
            return {
                "id": str(notebook.get("id", "")),
                "name": str(notebook.get("name", hint)),
            }

        current = self._current_notebook(event)
        if current:
            return current

        notebooks = await self._client().list_notebooks()
        if not notebooks:
            name = self._notebook_name_from_file(file_path)
            notebook = await self._client().create_notebook(name, "")
            self._set_current_notebook(event, notebook)
            return {
                "id": str(notebook.get("id", "")),
                "name": str(notebook.get("name", name)),
            }
        if len(notebooks) == 1 or allow_multi_auto:
            notebook = notebooks[0]
            self._set_current_notebook(event, notebook)
            return {
                "id": str(notebook.get("id", "")),
                "name": str(notebook.get("name", "未命名")),
            }

        raise ValueError(
            "当前有多个 notebook，请先使用 /on use <序号、名称或ID> 选择：\n"
            f"{self._format_notebooks(notebooks)}"
        )

    def _set_current_notebook(
        self, event: AstrMessageEvent, notebook: dict[str, Any]
    ) -> None:
        self.session_store.set(
            self._session_id(event),
            str(notebook.get("id", "")),
            str(notebook.get("name", "")),
        )

    @staticmethod
    def _notebook_name_from_file(file_path: Path) -> str:
        name = Path(file_path).stem.strip()
        return name or "AstrBot"

    async def _get_attached_file(self, event: AstrMessageEvent) -> Path:
        for component in event.message_obj.message:
            if isinstance(component, Comp.File):
                file_path = await component.get_file()
                if file_path:
                    return Path(file_path)
            if isinstance(component, Comp.Reply) and component.chain:
                for reply_component in component.chain:
                    if isinstance(reply_component, Comp.File):
                        file_path = await reply_component.get_file()
                        if file_path:
                            return Path(file_path)
        raise ValueError(
            "没有找到可上传的文件。请在同一条消息中附带或引用文件后使用 /on upload。"
        )

    async def _ask_current(self, event: AstrMessageEvent, question: str) -> str:
        current = self._current_notebook(event)
        if not current:
            return "请先使用 /on use <名称或ID> 选择 notebook。"
        if not question.strip():
            return "请提供要询问的问题。"
        try:
            return await self._client().ask(current["id"], question.strip())
        except Exception as exc:
            logger.error(f"Open Notebook ask failed: {exc}")
            return f"查询失败：{exc}"

    @staticmethod
    def _format_notebooks(notebooks: list[dict[str, Any]]) -> str:
        if not notebooks:
            return "Open Notebook 中暂无 notebook。"
        lines = ["Open Notebook notebooks："]
        for index, notebook in enumerate(notebooks, start=1):
            name = notebook.get("name", "未命名")
            notebook_id = notebook.get("id", "")
            lines.append(f"{index}. {name} ({notebook_id})")
        return "\n".join(lines)

    @staticmethod
    def _help_text() -> str:
        return "\n".join(
            [
                "Open Notebook 命令：",
                "/on ls - 列出 notebooks",
                "/on create <名称> [描述] - 创建并切换 notebook",
                "/on use <序号、名称或ID> - 切换 notebook，例如 /on use 1",
                "/on current - 查看当前 notebook",
                "/on upload - 上传当前或引用消息中的文件；0 个 notebook 会自动创建，1 个会自动使用",
                "/on ask <问题> - 查询当前 notebook",
                "/on delete <序号、名称或ID> - 删除 notebook",
                "/on help - 显示本帮助",
            ]
        )

    async def terminate(self):
        """AstrBot unload hook."""
        return None
