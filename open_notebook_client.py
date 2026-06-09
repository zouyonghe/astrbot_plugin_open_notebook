import json
from pathlib import Path
from typing import Any

import httpx


class OpenNotebookClient:
    def __init__(
        self,
        base_url: str,
        api_password: str = "",
        *,
        http_client: httpx.AsyncClient | None = None,
    ):
        self.base_url = self._normalize_base_url(base_url)
        self.api_password = api_password.strip()
        self._client = http_client

    async def health(self) -> dict[str, Any]:
        return await self._request_json("GET", "/health", use_api_prefix=False)

    async def list_notebooks(self) -> list[dict[str, Any]]:
        data = await self._request_json("GET", "/notebooks")
        if isinstance(data, list):
            return data
        raise ValueError("Open Notebook returned an invalid notebooks response.")

    async def create_notebook(self, name: str, description: str = "") -> dict[str, Any]:
        return await self._request_json(
            "POST",
            "/notebooks",
            json={"name": name, "description": description},
        )

    async def delete_notebook(self, notebook_id: str) -> dict[str, Any]:
        return await self._request_json("DELETE", f"/notebooks/{notebook_id}")

    async def list_credentials(
        self, provider: str | None = None
    ) -> list[dict[str, Any]]:
        params = {"provider": provider} if provider else None
        data = await self._request_json("GET", "/credentials", params=params)
        if isinstance(data, list):
            return data
        raise ValueError("Open Notebook returned an invalid credentials response.")

    async def create_credential(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request_json("POST", "/credentials", json=payload)

    async def update_credential(
        self,
        credential_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._request_json(
            "PUT",
            f"/credentials/{credential_id}",
            json=payload,
        )

    async def list_models(self, model_type: str | None = None) -> list[dict[str, Any]]:
        params = {"type": model_type} if model_type else None
        data = await self._request_json("GET", "/models", params=params)
        if isinstance(data, list):
            return data
        raise ValueError("Open Notebook returned an invalid models response.")

    async def create_model(
        self,
        name: str,
        provider: str,
        model_type: str,
        credential_id: str | None,
    ) -> dict[str, Any]:
        return await self._request_json(
            "POST",
            "/models",
            json={
                "name": name,
                "provider": provider,
                "type": model_type,
                "credential": credential_id,
            },
        )

    async def get_default_models(self) -> dict[str, Any]:
        data = await self._request_json("GET", "/models/defaults")
        if isinstance(data, dict):
            return data
        raise ValueError("Open Notebook returned an invalid default models response.")

    async def update_default_models(self, defaults: dict[str, Any]) -> dict[str, Any]:
        return await self._request_json("PUT", "/models/defaults", json=defaults)

    async def sync_model(
        self,
        *,
        credential_name: str,
        provider: str,
        model_name: str,
        api_key: str,
        base_url: str | None,
        model_type: str = "language",
    ) -> dict[str, Any]:
        credential = await self._sync_credential(
            credential_name=credential_name,
            provider=provider,
            api_key=api_key,
            base_url=base_url,
            model_type=model_type,
        )
        model = await self._sync_model_record(
            model_name=model_name,
            provider=provider,
            model_type=model_type,
            credential_id=str(credential.get("id", "")) or None,
        )
        defaults = await self.get_default_models()
        defaults["default_chat_model"] = model.get("id")
        defaults = await self.update_default_models(defaults)
        return {"credential": credential, "model": model, "defaults": defaults}

    async def _sync_credential(
        self,
        *,
        credential_name: str,
        provider: str,
        api_key: str,
        base_url: str | None,
        model_type: str,
    ) -> dict[str, Any]:
        payload = {
            "name": credential_name,
            "provider": provider,
            "modalities": [model_type],
            "api_key": api_key or None,
            "base_url": base_url or None,
        }
        credentials = await self.list_credentials(provider)
        for credential in credentials:
            if credential.get("name") == credential_name:
                update_payload = {
                    key: value for key, value in payload.items() if key != "provider"
                }
                return await self.update_credential(
                    str(credential["id"]), update_payload
                )
        return await self.create_credential(payload)

    async def _sync_model_record(
        self,
        *,
        model_name: str,
        provider: str,
        model_type: str,
        credential_id: str | None,
    ) -> dict[str, Any]:
        models = await self.list_models(model_type)
        for model in models:
            if (
                model.get("name") == model_name
                and model.get("provider") == provider
                and model.get("type") == model_type
            ):
                return model
        return await self.create_model(model_name, provider, model_type, credential_id)

    async def upload_file(
        self,
        notebook_id: str,
        file_path: Path,
        *,
        title: str | None,
        embed: bool,
        async_processing: bool,
    ) -> dict[str, Any]:
        path = Path(file_path)
        data = {
            "type": "upload",
            "notebooks": json.dumps([notebook_id]),
            "title": title or path.name,
            "embed": str(embed).lower(),
            "async_processing": str(async_processing).lower(),
        }
        with path.open("rb") as file_obj:
            files = {
                "file": (path.name, file_obj, "application/octet-stream"),
            }
            return await self._request_json("POST", "/sources", data=data, files=files)

    async def ask(self, notebook_id: str, question: str) -> str:
        session = await self._request_json(
            "POST",
            "/chat/sessions",
            json={"notebook_id": notebook_id, "title": question[:40] or "AstrBot"},
        )
        session_id = session.get("id")
        if not session_id:
            raise ValueError("Open Notebook did not return a chat session id.")

        context = await self._request_json(
            "POST",
            "/chat/context",
            json={"notebook_id": notebook_id, "context_config": {}},
        )
        result = await self._request_json(
            "POST",
            "/chat/execute",
            json={
                "session_id": session_id,
                "message": question,
                "context": context.get("context", {}),
            },
        )
        messages = result.get("messages", [])
        for message in reversed(messages):
            if message.get("type") in {"ai", "assistant"} and message.get("content"):
                return str(message["content"])
        return "Open Notebook 已处理问题，但没有返回可显示的回答。"

    async def aclose(self) -> None:
        if self._client:
            await self._client.aclose()

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        use_api_prefix: bool = True,
        **kwargs: Any,
    ) -> Any:
        client = self._client or httpx.AsyncClient(timeout=60)
        close_client = self._client is None
        try:
            response = await client.request(
                method,
                self._url(path, use_api_prefix=use_api_prefix),
                headers=self._headers(),
                **kwargs,
            )
            if response.is_error:
                raise RuntimeError(self._error_message(response))
            if not response.content:
                return {}
            return response.json()
        finally:
            if close_client:
                await client.aclose()

    def _headers(self) -> dict[str, str]:
        if not self.api_password:
            return {}
        return {"Authorization": f"Bearer {self.api_password}"}

    @staticmethod
    def _error_message(response: httpx.Response) -> str:
        try:
            data = response.json()
        except ValueError:
            data = None
        if isinstance(data, dict) and data.get("detail"):
            return str(data["detail"])
        return f"Open Notebook API error {response.status_code}: {response.text[:500]}"

    def _url(self, path: str, *, use_api_prefix: bool = True) -> str:
        clean_path = path if path.startswith("/") else f"/{path}"
        if use_api_prefix:
            return f"{self.base_url}/api{clean_path}"
        return f"{self.base_url}{clean_path}"

    @staticmethod
    def _normalize_base_url(base_url: str) -> str:
        value = (base_url or "http://localhost:5055").strip().rstrip("/")
        if value.endswith("/api"):
            value = value[:-4]
        return value or "http://localhost:5055"
