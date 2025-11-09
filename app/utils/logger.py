"""
Structured logging utility for AARIS (Academic Agentic Review Intelligence System)
"""

import sys
import traceback
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Union
import importlib

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
        # Validate and sanitize log_dir to prevent path traversal
        log_path = Path(log_dir).resolve()
        base_dir = Path.cwd().resolve()

        # Ensure log_dir is within the current working directory
        try:
            log_path.relative_to(base_dir)
        except ValueError:
            # If log_path is outside base_dir, use default safe location
            log_path = base_dir / "logs"

        self.log_dir = log_path
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

        # Ensure directory creation is attempted but won't raise outwards on failure.
        self._ensure_log_directory()
        self._log_cache = set()
        self.default_context = {
            "AI Engineer": "Muhammad",
            "system": "AARIS",
            "component": "backend",
        }

    def _ensure_log_directory(self) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _get_caller_info() -> tuple[str, str]:
        try:
            # sys._getframe is faster than inspect.currentframe
            # 2 levels up to get the caller of the logging method.
            frame = sys._getframe(2)
            current_function = frame.f_code.co_name
            parent_frame = frame.f_back
            parent_function = parent_frame.f_code.co_name if parent_frame else "Unknown"
        except (ValueError, AttributeError):
            current_function = "Unknown"
            parent_function = "Unknown"
        return current_function, parent_function

    def _format_message(
        self,
        level: LogLevel,
        message: str,
        error: Optional[BaseException] = None,
        additional_info: Optional[Dict[str, Any]] = None,
        exc_info: bool = False,
    ) -> str:
        """Format the complete log message with all metadata by delegating to helpers."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        current_function, _ = self._get_caller_info()
        # Redact message as first step
        safe_message = _redact_string(message)


        log_msg = [
            "=" * 80,
            f"TIMESTAMP: {timestamp}",
            f"LEVEL: {level.value}",
            f"FUNCTION: {current_function}",
            f"MESSAGE: {safe_message}",
        ]

        redacted_info = None
        if error:
            log_msg.extend(self._render_error_section(error, exc_info))

        # Create a copy to avoid modifying the instance-level default context
        log_context = self.default_context.copy()

        if additional_info:
            try:
                redacted_info = _deep_redact(additional_info)
                log_context.update(redacted_info)
            except Exception as e:
        # Redact any secrets in context fields
        log_context = _deep_redact(log_context)
                log_context["additional_info_error"] = f"Failed to merge additional_info: {e}"

        context_str = self._render_context(log_context)

        log_msg.extend(
            [
                "-" * 80,
                "CONTEXT:",
                context_str,
                "=" * 80 + "\n",
            ]
        )

        return "\n".join(log_msg)

    def _render_error_section(self, error: BaseException, exc_info: bool = False) -> list[str]:
        """Render error type/message and optional traceback into log lines."""
        lines = [
            f"ERROR TYPE: {type(error).__name__}",
            f"ERROR MESSAGE: {str(error)}",
            "-" * 80,
        ]

        if exc_info:
            try:
                trace_lines = traceback.format_exception(type(error), error, error.__traceback__)
                lines.extend(["FULL TRACEBACK:", "".join(trace_lines)])
            except Exception as e:
                lines.append(f"Failed to format traceback: {str(e)}")

        return lines

    def _render_context(self, context: Dict[str, Any]) -> str:
        """Safely render context dict entries into a string."""
        try:
            context_lines = []
            for k, v in context.items():
                try:
                    v_str = str(v)
                except Exception:
                    try:
                        v_str = repr(v)
                    except Exception:
                        v_str = "<unrepresentable>"
                context_lines.append(f"{k}: {v_str}")
            return "\n".join(context_lines)
        except Exception as e:
            return f"Failed to render context: {e}"

    def _merge_context(
        self, base_context: Dict[str, Any], additional_info: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Safely merge additional info into a base context dictionary."""
        if additional_info:
            try:
                base_context.update(additional_info)
            except Exception as e:
                base_context["additional_info_error"] = f"Failed to merge additional_info: {e}"
        return base_context

    def _write_log(self, level: LogLevel, message: str, custom_file: Optional[Path] = None) -> None:
        try:
            # Ensure message is redacted before hashing and writing
            redacted_message = _redact_string(message)
            log_hash = hash(redacted_message)
            if log_hash in self._log_cache:
                return
        except TypeError:
            log_hash = None  # Message is not hashable, cannot check for duplicates.

        try:
            self._ensure_log_directory()

            target_file = custom_file if custom_file else self.log_files[level]

            with open(target_file, "a", encoding="utf-8") as f:
                f.write(redacted_message)
            if log_hash is not None:
                self._log_cache.add(log_hash)
        except (IOError, PermissionError) as e:
            print(f"Failed to write log: {e}", file=sys.stderr)

    def debug(self, message: str, additional_info: Optional[Dict[str, Any]] = None) -> None:
        formatted = self._format_message(LogLevel.DEBUG, message, additional_info=additional_info)
        self._write_log(LogLevel.DEBUG, formatted)

    def info(self, message: str, additional_info: Optional[Dict[str, Any]] = None) -> None:
        formatted = self._format_message(LogLevel.INFO, message, additional_info=additional_info)
        self._write_log(LogLevel.INFO, formatted)

    def warning(self, message: str, additional_info: Optional[Dict[str, Any]] = None) -> None:
        formatted = self._format_message(LogLevel.WARNING, message, additional_info=additional_info)
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

    def exception(self, message: str, additional_info: Optional[Dict[str, Any]] = None) -> None:
        # Safely obtain the current exception info; if retrieval fails, treat as no exception.
        try:
            _, exc_value, _ = sys.exc_info()
        except Exception:
            exc_value = None

        # Do not mutate caller-provided additional_info; create a safe copy and ensure message is included.
        try:
            safe_additional = dict(additional_info) if additional_info else {}
        except (TypeError, ValueError):
            safe_additional = {
                "additional_info_error": "Provided additional_info is not a valid dictionary."
            }

        if "message" not in safe_additional:
            safe_additional["message"] = message

        # Only pass a real exception object to self.error with exc_info=True.
        if isinstance(exc_value, BaseException):
            self.error(
                exc_value,
                additional_info=safe_additional,
                exc_info=True,
            )
        else:
            # No active exception context: log a synthetic Exception with exc_info disabled.
            self.error(Exception(message), additional_info=safe_additional, exc_info=False)

    # AARIS-specific logging methods
    def log_agent_activity(
        self,
        agent_type: str,
        action: str,
        submission_id: str,
        additional_info: Optional[Dict[str, Any]] = None,
    ) -> None:
        context = {
            "agent_type": agent_type,
            "action": action,
            "submission_id": submission_id,
            "component": "agent_system",
        }
        context = self._merge_context(context, additional_info)

        message = f"Agent {agent_type} performed {action} for submission {submission_id}"
        formatted = self._format_message(LogLevel.INFO, message, additional_info=context)
        self._write_log(LogLevel.INFO, formatted, custom_file=self.agent_log)

    def log_review_process(
        self,
        submission_id: str,
        stage: str,
        status: str,
        additional_info: Optional[Dict[str, Any]] = None,
    ) -> None:
        context = {
            "submission_id": submission_id,
            "stage": stage,
            "status": status,
            "component": "review_system",
        }
        context = self._merge_context(context, additional_info)

        message = f"Review {submission_id} at stage {stage} is {status}"
        formatted = self._format_message(LogLevel.INFO, message, additional_info=context)
        self._write_log(LogLevel.INFO, formatted, custom_file=self.review_log)

    def log_api_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        additional_info: Optional[Dict[str, Any]] = None,
    ) -> None:
        context = {
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "component": "api_system",
        }
        context = self._merge_context(context, additional_info)

        message = f"{method} {endpoint} - Status: {status_code}"
        formatted = self._format_message(LogLevel.INFO, message, additional_info=context)
        self._write_log(LogLevel.INFO, formatted, custom_file=self.api_log)

    def clear_logs(self, level: Optional[LogLevel] = None) -> None:
        try:
            targets = (
                [self.log_files[level]]
                if level
                else list(self.log_files.values()) + [self.agent_log, self.review_log, self.api_log]
            )

            for file_path in targets:
                try:
                    # Security: ensure the path is within the intended log directory
                    resolved_path = file_path.resolve()
                    if self.log_dir not in resolved_path.parents:
                        print(
                            f"Skipping unsafe log clear attempt for: {file_path}", file=sys.stderr
                        )
                        continue

                    with open(resolved_path, "w", encoding="utf-8") as f:
                        f.write("")
                except Exception as e:
                    print(f"Failed to clear log {file_path}: {e}", file=sys.stderr)

            self._log_cache.clear()
        except Exception as e:
            print(f"Failed to clear logs: {e}", file=sys.stderr)


# Global logger instance
aaris_logger = AARISLogger()


def get_logger(_name: Optional[str] = None) -> AARISLogger:
    """Get logger instance"""
    return aaris_logger
