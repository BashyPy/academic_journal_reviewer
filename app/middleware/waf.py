"""Web Application Firewall middleware"""

import re
from typing import List

from fastapi import Request
from fastapi.responses import JSONResponse

from app.utils.logger import get_logger

logger = get_logger(__name__)


class WAF:
    """Simple WAF implementation"""

    SQL_INJECTION_PATTERNS = [
        r"(\bunion\b.*\bselect\b)",
        r"(\bselect\b.*\bfrom\b)",
        r"(\binsert\b.*\binto\b)",
        r"(\bdelete\b.*\bfrom\b)",
        r"(\bdrop\b.*?\btable\b)",
        r"(--|\#|\/\*)",
        r"(\bor\b.*?=.*?)",
        r"(\band\b.*?=.*?)",
    ]

    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"onerror\s*=",
        r"onload\s*=",
        r"<iframe",
        r"<object",
        r"<embed",
    ]

    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"/\.\.(?![a-zA-Z0-9])",  # /.. not followed by alphanum
        r"\\.\.(?![a-zA-Z0-9])",  # \.. not followed by alphanum
        r"%2e%2e/",
        r"/%2e%2e(?![a-zA-Z0-9])",
        r"\.\.\\",
    ]

    COMMAND_INJECTION_PATTERNS = [
        r";\s*(ls|cat|wget|curl|nc|bash|sh)",
        r"\|\s*(ls|cat|wget|curl|nc|bash|sh)",
        r"`.*`",
        r"\$\(.*\)",
    ]

    sql_regex = [re.compile(p, re.IGNORECASE) for p in SQL_INJECTION_PATTERNS]
    xss_regex = [re.compile(p, re.IGNORECASE) for p in XSS_PATTERNS]
    path_regex = [re.compile(p, re.IGNORECASE) for p in PATH_TRAVERSAL_PATTERNS]
    cmd_regex = [re.compile(p, re.IGNORECASE) for p in COMMAND_INJECTION_PATTERNS]

    def check_patterns(self, text: str, patterns: List[re.Pattern]) -> bool:
        """Check if text matches any pattern"""
        return any(pattern.search(text) for pattern in patterns)

    def _check_url(self, url: str) -> tuple[bool, str]:
        if self.check_patterns(url, self.sql_regex):
            return False, "SQL injection detected in URL"
        if self.check_patterns(url, self.xss_regex):
            return False, "XSS attempt detected in URL"
        if self.check_patterns(url, self.path_regex):
            return False, "Path traversal detected in URL"
        return True, "OK"

    def _check_headers(self, headers) -> tuple[bool, str]:
        safe_headers = {
            "accept",
            "accept-encoding",
            "accept-language",
            "content-type",
            "user-agent",
            "host",
            "connection",
        }
        for key, value in headers.items():
            if key.lower() in safe_headers:
                continue
            if self.check_patterns(value, self.sql_regex):
                return False, f"SQL injection detected in header: {key}"
            if self.check_patterns(value, self.xss_regex):
                return False, f"XSS attempt detected in header: {key}"
            if self.check_patterns(value, self.cmd_regex):
                return False, f"Command injection detected in header: {key}"
        return True, "OK"

    def _check_body(self, body: str) -> tuple[bool, str]:
        if not body:
            return True, "OK"

        checks = [
            (self.sql_regex, "SQL injection detected in body"),
            (self.xss_regex, "XSS attempt detected in body"),
            (self.cmd_regex, "Command injection detected in body"),
        ]

        for patterns, message in checks:
            if self.check_patterns(body, patterns):
                return False, message

        return True, "OK"

    def scan_request(self, request: Request, body: str = "") -> tuple[bool, str]:
        """Scan request for threats"""
        url = str(request.url)
        ok, msg = self._check_url(url)
        if not ok:
            return ok, msg

        ok, msg = self._check_headers(request.headers)
        if not ok:
            return ok, msg

        ok, msg = self._check_body(body)
        if not ok:
            return ok, msg

        return True, "OK"


waf = WAF()


async def waf_middleware(request: Request, call_next):
    """WAF middleware"""
    # Read body if present
    body = ""
    body_bytes = b""
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body_bytes = await request.body()
            body = body_bytes.decode("utf-8")

            # After reading the body, the stream is consumed.
            # We need to replace the request's receive channel with one that returns the cached body.
            def receive():
                return {"type": "http.request", "body": body_bytes, "more_body": False}

            request = Request(request.scope, receive=receive)

        except (ValueError, RuntimeError) as e:
            logger.warning(f"Failed to decode request body: {e}")
            body = ""

    # Scan request
    is_safe, message = waf.scan_request(request, body)

    if not is_safe:
        logger.warning(
            f"WAF blocked request: {message}",
            additional_info={
                "ip": request.client.host if request.client else "unknown",
                "path": str(request.url.path),
                "method": request.method,
            },
        )
        return JSONResponse(
            status_code=403,
            content={"detail": "Request blocked by security policy"},
        )

    response = await call_next(request)
    return response
