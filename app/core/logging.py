import logging
import json
from datetime import datetime
from typing import Any, Dict
import sys

class CustomJSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }
        
        # Include extra fields from the record
        if hasattr(record, "extra"):
            log_record.update(record.extra)
            
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_record)

def setup_logging():
    logger = logging.getLogger("translator")
    logger.setLevel(logging.INFO)
    
    # Console handler with JSON formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(CustomJSONFormatter())
    logger.addHandler(console_handler)
    
    # Add a custom log method that handles extra properties
    def _log_with_props(self, level: int, msg: str, props: Dict = None, **kwargs):
        """Custom logging method that handles additional properties"""
        extra = {"extra": props} if props else {}
        self.log(level, msg, extra=extra, **kwargs)
    
    # Add the custom method to the logger instance
    logger.info_with_props = lambda msg, props=None: _log_with_props(logger, logging.INFO, msg, props)
    logger.error_with_props = lambda msg, props=None: _log_with_props(logger, logging.ERROR, msg, props)
    logger.warning_with_props = lambda msg, props=None: _log_with_props(logger, logging.WARNING, msg, props)
    
    return logger

logger = setup_logging() 