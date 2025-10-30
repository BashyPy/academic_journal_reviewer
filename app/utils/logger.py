"""
Structured logging utility for AARIS (Academic Agentic Review Intelligence System)
"""

import inspect
import sys
import traceback
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Union


class LogLevel(Enum):
    """Logging severity levels"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AARISLogger:
    """
    Structured logging for AARIS system

    Features:
    - Level-specific log files
    - Duplicate prevention
    - Function call context
    - Error tracebacks
    - Agent-specific logging
    - Review process audit trail
    """

    def __init__(self, log_dir: Union[str, Path] = "logs"):
        base_logs_dir = Path.cwd() / "logs"
        log_dir_path = Path(log_dir).resolve()
        try:
            log_dir_path.relative_to(base_logs_dir)
        except ValueError:
            log_dir_path = base_logs_dir

        self.log_dir = log_dir_path
        self.log_files = {
            LogLevel.DEBUG: self.log_dir / "debug.log",
            LogLevel.INFO: self.log_dir / "info.log",
            LogLevel.WARNING: self.log_dir / "warning.log",
            LogLevel.ERROR: self.log_dir / "error.log",
            LogLevel.CRITICAL: self.log_dir / "critical.log",
        }

        # AARIS-specific log files
        self.agent_log = self.log_dir / "agents.log"
        self.review_log = self.log_dir / "reviews.log"
        self.api_log = self.log_dir / "api.log"

        self._ensure_log_directory()
        self._log_cache = set()

    def _ensure_log_directory(self) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _get_caller_info() -> tuple[str, str]:
        frame = inspect.currentframe()
        current_function = parent_function = "Unknown"
        if frame is not None:
            caller = frame.f_back
            parent = caller.f_back if caller and caller.f_back else None
            if caller:
                current_function = caller.f_code.co_name
            if parent:
                parent_function = parent.f_code.co_name
        return current_function, parent_function

    def _format_message(
        self,
        level: LogLevel,
        message: str,
        error: Optional[BaseException] = None,
        additional_info: Optional[Dict[str, Any]] = None,
        exc_info: bool = False,
    ) -> str:
        """Format the complete log message with all metadata."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        current_function, parent_function = self._get_caller_info()

        log_msg = [
            "=" * 80,
            f"TIMESTAMP: {timestamp}",
            f"LEVEL: {level.value}",
            f"FUNCTION: {current_function}",
            f"PARENT FUNCTION: {parent_function}",
            "-" * 80,
            f"MESSAGE: {message}",
        ]

        if error:
            log_msg.extend(
                [
                    f"ERROR TYPE: {type(error).__name__}",
                    f"ERROR MESSAGE: {str(error)}",
                    "-" * 80,
                ]
            )

            if exc_info:
                try:
                    trace_lines = traceback.format_exception(
                        type(error), error, error.__traceback__
                    )
                    log_msg.extend(["FULL TRACEBACK:", "".join(trace_lines)])
                except Exception as e:
                    log_msg.append(f"Failed to format traceback: {str(e)}")

        default_context = {
            "software_engineer": "Muhammad",
            "system": "AARIS",
            "component": "backend",
        }

        if additional_info:
            default_context.update(additional_info)

        log_msg.extend(
            [
                "-" * 80,
                "CONTEXT:",
                "\n".join(f"{k}: {v}" for k, v in default_context.items()),
                "=" * 80 + "\n",
            ]
        )

        return "\n".join(log_msg)

    def _write_log(
        self, level: LogLevel, message: str, custom_file: Optional[Path] = None
    ) -> None:
        log_hash = hash(message)
        if log_hash in self._log_cache:
            return

        try:
            self._ensure_log_directory()
            target_file = custom_file or self.log_files[level]
            with open(target_file, "a", encoding="utf-8") as f:
                f.write(message)
            self._log_cache.add(log_hash)
        except (IOError, PermissionError) as e:
            print(f"Failed to write log: {e}", file=sys.stderr)

    def debug(
        self, message: str, additional_info: Optional[Dict[str, Any]] = None
    ) -> None:
        formatted = self._format_message(
            LogLevel.DEBUG, message, additional_info=additional_info
        )
        self._write_log(LogLevel.DEBUG, formatted)

    def info(
        self, message: str, additional_info: Optional[Dict[str, Any]] = None
    ) -> None:
        formatted = self._format_message(
            LogLevel.INFO, message, additional_info=additional_info
        )
        self._write_log(LogLevel.INFO, formatted)

    def warning(
        self, message: str, additional_info: Optional[Dict[str, Any]] = None
    ) -> None:
        formatted = self._format_message(
            LogLevel.WARNING, message, additional_info=additional_info
        )
        self._write_log(LogLevel.WARNING, formatted)

    def error(
        self,
        error: BaseException,
        additional_info: Optional[Dict[str, Any]] = None,
        exc_info: bool = True,
    ) -> None:
        message = f"{type(error).__name__}: {str(error)}"
        formatted = self._format_message(
            LogLevel.ERROR,
            message,
            error=error,
            additional_info=additional_info,
            exc_info=exc_info,
        )
        self._write_log(LogLevel.ERROR, formatted)

    def critical(
        self,
        error: BaseException,
        additional_info: Optional[Dict[str, Any]] = None,
        exc_info: bool = True,
    ) -> None:
        message = f"{type(error).__name__}: {str(error)}"
        formatted = self._format_message(
            LogLevel.CRITICAL,
            message,
            error=error,
            additional_info=additional_info,
            exc_info=exc_info,
        )
        self._write_log(LogLevel.CRITICAL, formatted)

    def exception(
        self, message: str, additional_info: Optional[Dict[str, Any]] = None
    ) -> None:
        _, exc_value, _ = sys.exc_info()
        if exc_value is not None:
            self.error(
                exc_value,
                additional_info=additional_info or {"message": message},
                exc_info=True,
            )
        else:
            self.error(
                Exception(message), additional_info=additional_info, exc_info=False
            )

    # AARIS-specific logging methods
    def log_agent_activity(
        self,
        agent_type: str,
        action: str,
        submission_id: str,
        additional_info: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log agent-specific activities"""
        context = {
            "agent_type": agent_type,
            "action": action,
            "submission_id": submission_id,
            "component": "agent_system",
        }
        if additional_info:
            context.update(additional_info)

        message = (
            f"Agent {agent_type} performed {action} for submission {submission_id}"
        )
        formatted = self._format_message(
            LogLevel.INFO, message, additional_info=context
        )
        self._write_log(LogLevel.INFO, formatted, custom_file=self.agent_log)

    def log_review_process(
        self,
        submission_id: str,
        stage: str,
        status: str,
        additional_info: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log review process stages"""
        context = {
            "submission_id": submission_id,
            "stage": stage,
            "status": status,
            "component": "review_process",
        }
        if additional_info:
            context.update(additional_info)

        message = f"Review process for {submission_id}: {stage} - {status}"
        formatted = self._format_message(
            LogLevel.INFO, message, additional_info=context
        )
        self._write_log(LogLevel.INFO, formatted, custom_file=self.review_log)

    def log_api_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        additional_info: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log API requests"""
        context = {
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "component": "api",
        }
        if additional_info:
            context.update(additional_info)

        message = f"API {method} {endpoint} - Status: {status_code}"
        level = LogLevel.ERROR if status_code >= 400 else LogLevel.INFO
        formatted = self._format_message(level, message, additional_info=context)
        self._write_log(level, formatted, custom_file=self.api_log)

    def clear_logs(self, level: Optional[LogLevel] = None) -> None:
        try:
            targets = (
                [self.log_files[level]]
                if level
                else list(self.log_files.values())
                + [self.agent_log, self.review_log, self.api_log]
            )
            for file in targets:
                file_path = Path(file).resolve()
                if not str(file_path).startswith(str(self.log_dir.resolve())):
                    print(
                        f"Skipped clearing log file outside log directory: {file_path}",
                        file=sys.stderr,
                    )
                    continue
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("")
            self._log_cache.clear()
        except Exception as e:
            print(f"Failed to clear logs: {e}", file=sys.stderr)


# Global logger instance
aaris_logger = AARISLogger()


def get_logger(_name: Optional[str] = None) -> AARISLogger:
    """Get logger instance"""
    return aaris_logger
