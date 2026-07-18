from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AppendOnlyLedger:
    """A small hash-chained JSONL ledger for decisions and corrections."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        records: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(json.loads(line))
        return records

    @staticmethod
    def _hash(payload: dict[str, Any]) -> str:
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def append(self, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            records = self._records()
            previous_hash = records[-1]["record_hash"] if records else "GENESIS"
            record = {
                "index": len(records),
                "kind": kind,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "previous_hash": previous_hash,
                "payload": payload,
            }
            record["record_hash"] = self._hash(record)
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            return record

    def list(self, limit: int = 30) -> list[dict[str, Any]]:
        return list(reversed(self._records()[-limit:]))

    def records(self) -> list[dict[str, Any]]:
        return self._records()

    def verify(self) -> dict[str, Any]:
        records = self._records()
        previous_hash = "GENESIS"
        for expected_index, record in enumerate(records):
            recorded_hash = record.get("record_hash", "")
            unhashed = {k: v for k, v in record.items() if k != "record_hash"}
            if record.get("index") != expected_index:
                return {"valid": False, "records": len(records), "error": "index"}
            if record.get("previous_hash") != previous_hash:
                return {"valid": False, "records": len(records), "error": "chain"}
            if self._hash(unhashed) != recorded_hash:
                return {"valid": False, "records": len(records), "error": "hash"}
            previous_hash = recorded_hash
        return {"valid": True, "records": len(records), "head": previous_hash}
