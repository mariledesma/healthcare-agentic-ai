import json
from datetime import datetime, timezone
from pathlib import Path


class AuditLogger:
    def __init__(self, log_directory="results/audit_logs"):
        self.log_directory = Path(log_directory)
        self.log_directory.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        case_id,
        module,
        action,
        status,
        details=None
    ):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "case_id": case_id,
            "module": module,
            "action": action,
            "status": status,
            "details": details or {}
        }

        log_file = self.log_directory / f"{case_id.lower()}_audit.jsonl"

        with open(log_file, "a", encoding="utf-8") as file:
            file.write(json.dumps(log_entry) + "\n")

        return log_entry