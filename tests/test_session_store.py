import json
import tempfile
import unittest
from pathlib import Path

from session_store import SessionStore


class SessionStoreTest(unittest.TestCase):
    def test_stores_current_notebook_by_session_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SessionStore(Path(temp_dir) / "sessions.json")

            store.set("session-1", "notebook:abc", "Research")

            self.assertEqual(
                store.get("session-1"),
                {"id": "notebook:abc", "name": "Research"},
            )

    def test_clear_removes_only_target_session(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SessionStore(Path(temp_dir) / "sessions.json")
            store.set("session-1", "notebook:one", "One")
            store.set("session-2", "notebook:two", "Two")

            store.clear("session-1")

            self.assertIsNone(store.get("session-1"))
            self.assertEqual(
                store.get("session-2"),
                {"id": "notebook:two", "name": "Two"},
            )

    def test_recovers_from_invalid_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / "sessions.json"
            store_path.write_text("not json", encoding="utf-8")

            store = SessionStore(store_path)

            self.assertIsNone(store.get("missing"))
            store.set("session-1", "notebook:abc", "Research")
            self.assertEqual(json.loads(store_path.read_text(encoding="utf-8"))["session-1"]["id"], "notebook:abc")


if __name__ == "__main__":
    unittest.main()
