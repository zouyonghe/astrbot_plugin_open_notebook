import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import sys
import types

sys.path.append("/Users/buding/Code")


def _command_group(_name):
    def decorator(func):
        func.command = lambda _subcommand: lambda command_func: command_func
        return func

    return decorator


def _install_astrbot_stubs():
    astrbot = types.ModuleType("astrbot")
    api = types.ModuleType("astrbot.api")
    message_components = types.ModuleType("astrbot.api.message_components")
    event = types.ModuleType("astrbot.api.event")
    star = types.ModuleType("astrbot.api.star")
    core = types.ModuleType("astrbot.core")
    core_star = types.ModuleType("astrbot.core.star")
    core_star_filter = types.ModuleType("astrbot.core.star.filter")
    command = types.ModuleType("astrbot.core.star.filter.command")
    utils = types.ModuleType("astrbot.core.utils")
    astrbot_path = types.ModuleType("astrbot.core.utils.astrbot_path")

    class File:
        pass

    class Reply:
        pass

    class Star:
        pass

    class Context:
        pass

    class AstrMessageEvent:
        pass

    class AstrBotConfig(dict):
        pass

    class GreedyStr(str):
        pass

    message_components.File = File
    message_components.Reply = Reply
    api.message_components = message_components
    api.AstrBotConfig = AstrBotConfig
    api.logger = SimpleNamespace(error=lambda *args, **kwargs: None)
    event.AstrMessageEvent = AstrMessageEvent
    event.filter = SimpleNamespace(
        command_group=_command_group,
        llm_tool=lambda **_kwargs: lambda func: func,
    )
    star.Context = Context
    star.Star = Star
    star.register = lambda *_args, **_kwargs: lambda cls: cls
    command.GreedyStr = GreedyStr
    astrbot_path.get_astrbot_plugin_data_path = lambda: tempfile.gettempdir()

    sys.modules["astrbot"] = astrbot
    sys.modules["astrbot.api"] = api
    sys.modules["astrbot.api.message_components"] = message_components
    sys.modules["astrbot.api.event"] = event
    sys.modules["astrbot.api.star"] = star
    sys.modules["astrbot.core"] = core
    sys.modules["astrbot.core.star"] = core_star
    sys.modules["astrbot.core.star.filter"] = core_star_filter
    sys.modules["astrbot.core.star.filter.command"] = command
    sys.modules["astrbot.core.utils"] = utils
    sys.modules["astrbot.core.utils.astrbot_path"] = astrbot_path


_install_astrbot_stubs()

from astrbot_plugin_open_notebook.main import OpenNotebookPlugin  # noqa: E402


class FakeClient:
    def __init__(self, notebooks):
        self.notebooks = notebooks
        self.created = []
        self.uploads = []

    async def list_notebooks(self):
        return list(self.notebooks)

    async def create_notebook(self, name, description=""):
        notebook = {"id": f"notebook:{len(self.notebooks) + 1}", "name": name}
        self.notebooks.append(notebook)
        self.created.append((name, description))
        return notebook

    async def upload_file(self, notebook_id, file_path, **kwargs):
        self.uploads.append((notebook_id, Path(file_path), kwargs))
        return {"id": "source:uploaded"}


class FakeSessionStore:
    def __init__(self):
        self.values = {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, notebook_id, notebook_name):
        self.values[key] = {"id": notebook_id, "name": notebook_name}

    def clear(self, key):
        self.values.pop(key, None)


class FakeEvent:
    role = "admin"
    message_obj = SimpleNamespace(message=[])

    def get_platform_id(self):
        return "test"

    def get_session_id(self):
        return "session"

    def plain_result(self, text):
        return text


def make_plugin(client):
    plugin = OpenNotebookPlugin.__new__(OpenNotebookPlugin)
    plugin.config = {
        "embed_on_upload": True,
        "async_processing": True,
        "admin_only": False,
    }
    plugin.session_store = FakeSessionStore()
    plugin._client = lambda: client
    return plugin


class PluginBehaviorTest(unittest.TestCase):
    def test_finds_notebook_by_list_index(self):
        plugin = make_plugin(FakeClient([{"id": "notebook:abc", "name": "Research"}]))

        notebook = asyncio.run(plugin._find_notebook("1"))

        self.assertEqual(notebook["id"], "notebook:abc")

    def test_upload_uses_only_notebook_without_manual_switch(self):
        client = FakeClient([{"id": "notebook:abc", "name": "Research"}])
        plugin = make_plugin(client)
        event = FakeEvent()

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "paper.pdf"
            file_path.write_bytes(b"pdf")
            with patch.object(plugin, "_get_attached_file", return_value=file_path):
                results = asyncio.run(_collect(plugin.upload_document(event)))

        self.assertEqual(client.uploads[0][0], "notebook:abc")
        self.assertIn("Research", results[0])

    def test_upload_creates_notebook_when_none_exist(self):
        client = FakeClient([])
        plugin = make_plugin(client)
        event = FakeEvent()

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "paper.pdf"
            file_path.write_bytes(b"pdf")
            with patch.object(plugin, "_get_attached_file", return_value=file_path):
                results = asyncio.run(_collect(plugin.upload_document(event)))

        self.assertEqual(client.created[0][0], "paper")
        self.assertEqual(client.uploads[0][0], "notebook:1")
        self.assertIn("paper", results[0])

    def test_help_text_mentions_lifecycle_commands(self):
        help_text = OpenNotebookPlugin._help_text()

        self.assertIn("/on upload", help_text)
        self.assertIn("/on delete", help_text)
        self.assertIn("/on use 1", help_text)

    def test_tool_upload_creates_requested_notebook_when_missing(self):
        client = FakeClient([])
        plugin = make_plugin(client)
        event = FakeEvent()

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "galaxy.pdf"
            file_path.write_bytes(b"pdf")
            result = asyncio.run(
                plugin.tool_upload_file(
                    event,
                    str(file_path),
                    notebook="银河铁道资料",
                )
            )

        self.assertEqual(client.created[0][0], "银河铁道资料")
        self.assertEqual(client.uploads[0][0], "notebook:1")
        self.assertIn("银河铁道资料", result)


async def _collect(generator):
    return [item async for item in generator]


if __name__ == "__main__":
    unittest.main()
