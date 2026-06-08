import json
from pathlib import Path


class SessionStore:
    def __init__(self, path: Path):
        self.path = path

    def get(self, session_id: str) -> dict[str, str] | None:
        data = self._read()
        value = data.get(session_id)
        if not isinstance(value, dict):
            return None
        notebook_id = value.get("id")
        notebook_name = value.get("name")
        if not isinstance(notebook_id, str) or not isinstance(notebook_name, str):
            return None
        return {"id": notebook_id, "name": notebook_name}

    def set(self, session_id: str, notebook_id: str, notebook_name: str) -> None:
        data = self._read()
        data[session_id] = {"id": notebook_id, "name": notebook_name}
        self._write(data)

    def clear(self, session_id: str) -> None:
        data = self._read()
        data.pop(session_id, None)
        self._write(data)

    def _read(self) -> dict[str, dict[str, str]]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(data, dict):
            return {}
        return data

    def _write(self, data: dict[str, dict[str, str]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        temp_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp_path.replace(self.path)
