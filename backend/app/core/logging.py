import json
import logging
import sys
from contextvars import ContextVar, Token

_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")
_trace_ctx: ContextVar[str] = ContextVar("trace_id", default="")


def get_request_id() -> str:
    """Return the current request correlation ID."""
    return _request_id_ctx.get()


def set_request_id(request_id: str) -> Token[str]:
    """Bind a request correlation ID to the current async context."""
    return _request_id_ctx.set(request_id)


def reset_request_id(token: Token[str]) -> None:
    """Reset the request correlation ID ContextVar."""
    _request_id_ctx.reset(token)


def get_trace_id() -> str:
    """Return the current Google Cloud trace ID if present."""
    return _trace_ctx.get()


def set_trace_id(trace_id: str) -> Token[str]:
    """Bind a Google Cloud trace ID to the current async context."""
    return _trace_ctx.set(trace_id)


def reset_trace_id(token: Token[str]) -> None:
    """Reset the Google Cloud trace ID ContextVar."""
    _trace_ctx.reset(token)


class RequestIdFilter(logging.Filter):
    """Inject request_id and trace_id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        record.trace_id = get_trace_id()
        return True


class JsonLogFormatter(logging.Formatter):
    """Format log records as JSON compatible with Google Cloud Logging."""

    def __init__(self, gcp_project_id: str | None = None) -> None:
        super().__init__()
        self._gcp_project_id = (
            gcp_project_id.strip() if gcp_project_id and gcp_project_id.strip() else None
        )

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
        }
        trace_id = getattr(record, "trace_id", "")
        if trace_id:
            if self._gcp_project_id:
                payload["logging.googleapis.com/trace"] = (
                    f"projects/{self._gcp_project_id}/traces/{trace_id}"
                )
            else:
                payload["trace_id"] = trace_id
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str = "INFO", gcp_project_id: str | None = None) -> None:
    """Configure structured JSON application logging without exposing secrets."""
    resolved_level = getattr(logging, level.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(JsonLogFormatter(gcp_project_id=gcp_project_id))

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(resolved_level)
