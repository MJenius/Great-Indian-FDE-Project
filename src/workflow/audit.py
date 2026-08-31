"""
Audit logging facility for all workflow actions and mutations.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import AuditEntry, HttpMethod, WorkflowState


class AuditLogger:
    def __init__(self, log_file: Optional[Path] = None):
        self.entries: List[AuditEntry] = []
        self.log_file = log_file

    def log(
        self,
        task: str,
        state: WorkflowState,
        operation: HttpMethod,
        endpoint: str,
        target: str,
        request_summary: Dict[str, Any],
        status_code: Optional[int] = None,
        result: Optional[str] = None,
        verified: bool = False,
        error: Optional[str] = None,
    ) -> AuditEntry:
        now_str = datetime.now(timezone.utc).isoformat()
        
        # Scrub sensitive fields if any exist
        scrubbed_summary = self._scrub_sensitive(request_summary)

        entry = AuditEntry(
            timestamp=now_str,
            task=task,
            state=state,
            operation=operation,
            endpoint=endpoint,
            target=target,
            request_summary=scrubbed_summary,
            status_code=status_code,
            result=result,
            verified=verified,
            error=error,
        )
        self.entries.append(entry)

        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.model_dump()) + "\n")

        return entry

    def _scrub_sensitive(self, data: Dict[str, Any]) -> Dict[str, Any]:
        sensitive_keys = {"token", "api_key", "secret", "password", "authorization"}
        cleaned = {}
        for k, v in data.items():
            if k.lower() in sensitive_keys:
                cleaned[k] = "[REDACTED]"
            elif isinstance(v, dict):
                cleaned[k] = self._scrub_sensitive(v)
            else:
                cleaned[k] = v
        return cleaned

    def get_entries(self) -> List[AuditEntry]:
        return self.entries
