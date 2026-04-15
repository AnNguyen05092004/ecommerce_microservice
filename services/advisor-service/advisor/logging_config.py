import json
import logging
import uuid


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record):
        log_obj = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add request context if available
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_obj["user_id"] = record.user_id
        if hasattr(record, "operation"):
            log_obj["operation"] = record.operation
        if hasattr(record, "duration_ms"):
            log_obj["duration_ms"] = record.duration_ms
        if hasattr(record, "result_code"):
            log_obj["result_code"] = record.result_code
        if hasattr(record, "details"):
            log_obj["details"] = record.details

        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj, ensure_ascii=False)


def get_request_id():
    """Generate a unique request ID."""
    return str(uuid.uuid4())[:12]


def setup_logging(logger_name="advisor"):
    """Configure advisor logging with JSON formatter."""
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    # Remove existing handlers
    logger.handlers = []

    # Create console handler with JSON formatter
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(JSONFormatter())

    logger.addHandler(handler)
    return logger


class LogContext:
    """Context manager for adding logging context to a request."""

    def __init__(self, logger, request_id=None, user_id=None, operation=None):
        self.logger = logger
        self.request_id = request_id or get_request_id()
        self.user_id = user_id
        self.operation = operation

    def log(self, level, message, **kwargs):
        """Log with context."""
        extra = {
            "request_id": self.request_id,
            "user_id": self.user_id,
            "operation": self.operation,
        }
        extra.update(kwargs)
        self.logger.log(level, message, extra=extra)

    def info(self, message, **kwargs):
        self.log(logging.INFO, message, **kwargs)

    def debug(self, message, **kwargs):
        self.log(logging.DEBUG, message, **kwargs)

    def error(self, message, **kwargs):
        self.log(logging.ERROR, message, **kwargs)

    def warning(self, message, **kwargs):
        self.log(logging.WARNING, message, **kwargs)
