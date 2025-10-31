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
        # Normalize and sanitize the provided log_dir into a single safe directory name.
        candidate_name = "logs"
        try:
            if isinstance(log_dir, Path):
                candidate_name = log_dir.name or "logs"
            elif isinstance(log_dir, str):
                # Use only the final path segment to avoid traversal and strip disallowed chars.
                candidate_name = Path(log_dir).name or "logs"
                candidate_name = "".join(
                    c for c in candidate_name if c.isalnum() or c in ("-", "_")
                )
                if not candidate_name:
                    candidate_name = "logs"
            else:
                # Unexpected type, fall back to default.
                candidate_name = "logs"
        except Exception as e:
            print(f"Failed to sanitize log_dir ({log_dir}): {e}", file=sys.stderr)
            candidate_name = "logs"

        # Define a safe base directory for all logs to avoid using an undefined variable
        # and to prevent directory traversal; adjust this if you want a different base.
        base_logs_dir = Path.cwd() / "logs"

        log_dir_path = base_logs_dir / candidate_name

        # Ensure the resolved candidate is inside the base logs directory, with robust error handling.
        try:
            resolved_base = base_logs_dir.resolve()
            try:
                resolved_candidate = log_dir_path.resolve()
                # Use relative_to check; any exception means it's unsafe or resolution failed.
                try:
                    resolved_candidate.relative_to(resolved_base)
                except Exception:
                    # Not within base directory -> fallback to base.
                    log_dir_path = base_logs_dir
            except Exception:
                # If resolving candidate failed, fallback to base.
                log_dir_path = base_logs_dir
        except Exception:
            # If resolving base fails for any reason, fallback to a minimal safe path.
            log_dir_path = Path("logs")

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

        # Ensure directory creation is attempted but won't raise outwards on failure.
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
        """Format the complete log message with all metadata by delegating to helpers."""
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
            log_msg.extend(self._render_error_section(error, exc_info))

        default_context = {
            "software_engineer": "Muhammad",
            "system": "AARIS",
            "component": "backend",
        }

        if additional_info:
            try:
                default_context.update(additional_info)
            except Exception as e:
                # If merging additional_info fails, record the failure in the context instead of raising.
                default_context["additional_info_error"] = (
                    f"Failed to merge additional_info: {e}"
                )

        context_str = self._render_context(default_context)

        log_msg.extend(
            [
                "-" * 80,
                "CONTEXT:",
                context_str,
                "=" * 80 + "\n",
            ]
        )

        return "\n".join(log_msg)

    def _render_error_section(
        self, error: BaseException, exc_info: bool = False
    ) -> list[str]:
        """Render error type/message and optional traceback into log lines."""
        lines = [
            f"ERROR TYPE: {type(error).__name__}",
            f"ERROR MESSAGE: {str(error)}",
            "-" * 80,
        ]

        if exc_info:
            try:
                trace_lines = traceback.format_exception(
                    type(error), error, error.__traceback__
                )
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

    def _write_log(
        self, level: LogLevel, message: str, custom_file: Optional[Path] = None
    ) -> None:
        log_hash = hash(message)
        if log_hash in self._log_cache:
            return

        try:
            self._ensure_log_directory()

            # Resolve base directory without strict resolution to avoid exceptions if files do not exist yet.
            try:
                base_dir = self.log_dir.resolve(strict=False)
            except Exception:
                base_dir = self.log_dir

            # Pick the target file (custom or level-based) and resolve safely.
            candidate = (
                Path(custom_file)
                if custom_file is not None
                else Path(self.log_files[level])
            )
            try:
                candidate_resolved = candidate.resolve(strict=False)
                # Ensure the resolved candidate is within the base logs directory.
                try:
                    candidate_resolved.relative_to(base_dir)
                except Exception:
                    # Fallback to the level-specific file if candidate is outside base directory.
                    candidate_resolved = Path(self.log_files[level]).resolve(
                        strict=False
                    )
            except Exception:
                candidate_resolved = Path(self.log_files[level]).resolve(strict=False)

            # Ensure parent directories exist for the resolved target.
            try:
                candidate_resolved.parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                # If we can't create the parent, fallback to base level file parent.
                try:
                    fallback_parent = Path(self.log_files[level]).parent
                    fallback_parent.mkdir(parents=True, exist_ok=True)
                    candidate_resolved = Path(self.log_files[level]).resolve(
                        strict=False
                    )
                except Exception:
                    # Give up gracefully
                    print(
                        f"Failed to prepare log file: {candidate_resolved}",
                        file=sys.stderr,
                    )
                    return

            with open(candidate_resolved, "a", encoding="utf-8") as f:
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
        # Safely obtain the current exception info; if retrieval fails, treat as no exception.
        try:
            _, exc_value, _ = sys.exc_info()
        except Exception:
            exc_value = None

        # Do not mutate caller-provided additional_info; create a safe copy and ensure message is included.
        safe_additional = dict(additional_info) if additional_info else {}
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
            self.error(
                Exception(message), additional_info=safe_additional, exc_info=False
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
            "component": "review_system",
        }
        if additional_info:
            try:
                context.update(additional_info)
            except Exception as e:
                context["additional_info_error"] = (
                    f"Failed to merge additional_info: {e}"
                )

        message = f"Review {submission_id} at stage {stage} is {status}"
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
        """Log API request details"""
        context = {
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "component": "api_system",
        }
        if additional_info:
            try:
                context.update(additional_info)
            except Exception as e:
                context["additional_info_error"] = (
                    f"Failed to merge additional_info: {e}"
                )

        message = f"{method} {endpoint} - Status: {status_code}"
        formatted = self._format_message(
            LogLevel.INFO, message, additional_info=context
        )
        self._write_log(LogLevel.INFO, formatted, custom_file=self.api_log)

    def clear_logs(self, level: Optional[LogLevel] = None) -> None:
        try:
            targets = (
                [self.log_files[level]]
                if level
                else list(self.log_files.values())
                + [self.agent_log, self.review_log, self.api_log]
            )

            # Resolve base log dir without strict resolution to avoid exceptions if files do not exist yet.
            try:
                base_log_dir = self.log_dir.resolve(strict=False)
            except Exception:
                base_log_dir = self.log_dir

            for file in targets:
                try:
                    file_path = Path(file).resolve(strict=False)
                except Exception:
                    print(
                        f"Security: Could not resolve path for: {file}", file=sys.stderr
                    )
                    continue

                # Security check: ensure file is within log directory
                try:
                    file_path.relative_to(base_log_dir)
                except Exception:
                    print(
                        f"Security: Skipped clearing log file outside log directory: {file_path}",
                        file=sys.stderr,
                    )
                    continue

                # Additional security: check file extension
                if file_path.suffix not in (".log", ".txt"):
                    print(
                        f"Security: Skipped clearing non-log file: {file_path}",
                        file=sys.stderr,
                    )
                    continue

                try:
                    # Ensure parent exists and then truncate file
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write("")
                except Exception as e:
                    print(f"Failed to clear log {file_path}: {e}", file=sys.stderr)
                    continue

            self._log_cache.clear()
        except Exception as e:
            print(f"Failed to clear logs: {e}", file=sys.stderr)


# Global logger instance
aaris_logger = AARISLogger()


def get_logger(_name: Optional[str] = None) -> AARISLogger:
    """Get logger instance"""
    return aaris_logger
