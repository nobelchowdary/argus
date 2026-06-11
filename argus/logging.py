"""Structured JSONL logger for Argus — every tool call and agent action is logged."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("argus")


class JsonlHandler(logging.Handler):
    """Writes structured JSONL to a file."""

    def __init__(self, filepath: Path | str):
        super().__init__()
        self.filepath = Path(filepath)
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(self.filepath, "a")  # noqa: SIM115

    def emit(self, record: logging.LogRecord):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
        }
        if hasattr(record, "extra_data"):
            entry["data"] = record.extra_data
        self._file.write(json.dumps(entry) + "\n")
        self._file.flush()

    def close(self):
        self._file.close()
        super().close()


def setup_logging(log_dir: str = "logs", level: int = logging.INFO) -> logging.Logger:
    """Configure Argus logging with both console and JSONL outputs."""
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    argus_logger = logging.getLogger("argus")
    argus_logger.setLevel(level)

    if not argus_logger.handlers:
        # Console handler
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(level)
        console.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        argus_logger.addHandler(console)

        # JSONL handler
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        jsonl_handler = JsonlHandler(log_path / f"argus_{timestamp}.jsonl")
        argus_logger.addHandler(jsonl_handler)

    return argus_logger


def log_tool_call(
    tool_name: str,
    case_id: str,
    args: dict[str, Any],
    result_summary: str = "",
    execution_time_ms: int = 0,
):
    """Log a tool call with structured data."""
    record = logger.makeRecord(
        name="argus.tools",
        level=logging.INFO,
        fn="",
        lno=0,
        msg=f"Tool call: {tool_name} for case {case_id}",
        args=(),
        exc_info=None,
    )
    record.extra_data = {
        "tool_name": tool_name,
        "case_id": case_id,
        "args": args,
        "result_summary": result_summary,
        "execution_time_ms": execution_time_ms,
    }
    logger.handle(record)


def log_agent_action(
    agent: str,
    action: str,
    case_id: str,
    details: dict[str, Any] | None = None,
):
    """Log an agent action (investigator draft, skeptic verdict, etc.)."""
    record = logger.makeRecord(
        name=f"argus.{agent}",
        level=logging.INFO,
        fn="",
        lno=0,
        msg=f"{agent}: {action} for case {case_id}",
        args=(),
        exc_info=None,
    )
    record.extra_data = {
        "agent": agent,
        "action": action,
        "case_id": case_id,
        "details": details or {},
    }
    logger.handle(record)
