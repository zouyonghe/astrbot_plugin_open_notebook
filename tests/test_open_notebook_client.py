import asyncio
import json
import tempfile
import unittest
from pathlib import Path

import httpx

from open_notebook_client import OpenNotebookClient


class OpenNotebookClientTest(unittest.TestCase):
    def test_lists_notebooks_with_bearer_auth_and_api_prefix(self):
        requests = []

        async def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(
                200, json=[{"id": "notebook:abc", "name": "Research"}]
            )

        client = OpenNotebookClient(
            "http://open-notebook.local/api/",
            "secret",
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )

        result = asyncio.run(client.list_notebooks())

        self.assertEqual(result[0]["id"], "notebook:abc")
        self.assertEqual(
            str(requests[0].url), "http://open-notebook.local/api/notebooks"
        )
        self.assertEqual(requests[0].headers["authorization"], "Bearer secret")

    def test_creates_notebook(self):
        async def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content.decode("utf-8"))
            self.assertEqual(body, {"name": "Research", "description": "Docs"})
            return httpx.Response(200, json={"id": "notebook:abc", "name": "Research"})

        client = OpenNotebookClient(
            "http://open-notebook.local",
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )

        result = asyncio.run(client.create_notebook("Research", "Docs"))

        self.assertEqual(result["id"], "notebook:abc")

    def test_uploads_file_to_selected_notebook(self):
        seen_body = b""

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal seen_body
            seen_body = request.content
            return httpx.Response(
                200,
                json={
                    "id": "source:abc",
                    "title": "paper.pdf",
                    "topics": [],
                    "created": "now",
                    "updated": "now",
                },
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "paper.pdf"
            file_path.write_bytes(b"pdf bytes")
            client = OpenNotebookClient(
                "http://open-notebook.local",
                http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
            )

            result = asyncio.run(
                client.upload_file(
                    "notebook:abc",
                    file_path,
                    title=None,
                    embed=True,
                    async_processing=True,
                )
            )

        self.assertEqual(result["id"], "source:abc")
        self.assertIn(b'name="type"', seen_body)
        self.assertIn(b"upload", seen_body)
        self.assertIn(b'name="notebooks"', seen_body)
        self.assertIn(b'["notebook:abc"]', seen_body)
        self.assertIn(b'name="embed"', seen_body)
        self.assertIn(b"true", seen_body)
        self.assertIn(b'filename="paper.pdf"', seen_body)

    def test_raises_open_notebook_error_detail(self):
        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                500,
                json={"detail": "No model configured for default for type=chat."},
            )

        client = OpenNotebookClient(
            "http://open-notebook.local",
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "No model configured for default for type=chat",
        ):
            asyncio.run(client.list_notebooks())

    def test_syncs_credential_model_and_defaults(self):
        seen = []

        async def handler(request: httpx.Request) -> httpx.Response:
            seen.append(
                (request.method, str(request.url), request.content.decode("utf-8"))
            )
            if request.method == "GET" and request.url.path == "/api/models/defaults":
                return httpx.Response(
                    200,
                    json={
                        "default_chat_model": "",
                        "default_transformation_model": None,
                        "large_context_model": None,
                        "default_text_to_speech_model": None,
                        "default_speech_to_text_model": None,
                        "default_embedding_model": None,
                        "default_tools_model": None,
                    },
                )
            if request.method == "GET" and request.url.path == "/api/credentials":
                return httpx.Response(200, json=[])
            if request.method == "GET" and request.url.path == "/api/models":
                return httpx.Response(200, json=[])
            if request.method == "POST" and request.url.path == "/api/credentials":
                return httpx.Response(
                    201,
                    json={
                        "id": "cred:1",
                        "name": "AstrBot default",
                        "provider": "openai_compatible",
                        "modalities": ["language"],
                        "created": "now",
                        "updated": "now",
                    },
                )
            if request.method == "POST" and request.url.path == "/api/models":
                return httpx.Response(
                    200,
                    json={
                        "id": "model:1",
                        "name": "gpt-5.5",
                        "provider": "openai_compatible",
                        "type": "language",
                        "credential": "cred:1",
                        "created": "now",
                        "updated": "now",
                    },
                )
            if request.method == "PUT" and request.url.path == "/api/models/defaults":
                return httpx.Response(
                    200,
                    json={
                        "default_chat_model": "model:1",
                        "default_transformation_model": None,
                        "large_context_model": None,
                        "default_text_to_speech_model": None,
                        "default_speech_to_text_model": None,
                        "default_embedding_model": None,
                        "default_tools_model": None,
                    },
                )
            raise AssertionError(f"unexpected request {request.method} {request.url}")

        client = OpenNotebookClient(
            "http://open-notebook.local",
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )

        result = asyncio.run(
            client.sync_model(
                credential_name="AstrBot default",
                provider="openai_compatible",
                model_name="gpt-5.5",
                api_key="secret",
                base_url="http://localhost:8000/v1",
                model_type="language",
            )
        )

        self.assertEqual(result["credential"]["id"], "cred:1")
        self.assertEqual(result["model"]["id"], "model:1")
        self.assertEqual(result["defaults"]["default_chat_model"], "model:1")
        self.assertTrue(
            any(
                method == "POST" and url.endswith("/api/credentials")
                for method, url, _ in seen
            )
        )
        self.assertTrue(
            any(
                method == "POST" and url.endswith("/api/models")
                for method, url, _ in seen
            )
        )
        self.assertTrue(
            any(
                method == "PUT" and url.endswith("/api/models/defaults")
                for method, url, _ in seen
            )
        )


if __name__ == "__main__":
    unittest.main()
