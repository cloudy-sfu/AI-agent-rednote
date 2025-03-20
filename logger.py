import logging.handlers
import os
from datetime import datetime


class ListLoggingHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        # List of dictionaries with keys: levelname, asctime, filename, message
        self.records: list[dict[str, str]] = []

    def emit(self, record: logging.LogRecord) -> None:
        # Format record creation time to a human-readable string
        asctime = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        # Construct the log dictionary
        log_entry = {
            'levelname': record.levelname,
            'asctime': asctime,
            'filename': record.filename,
            'message': record.getMessage()
        }
        self.records.append(log_entry)

    def display(self, n: int = 50):
        return self.records[-n:]


def get_file_handler():
    os.makedirs('log', exist_ok=True)
    formatter = logging.Formatter(
        '# %(levelname)s | %(asctime)s | %(filename)s\n%(message)s')
    handler_1 = logging.handlers.RotatingFileHandler('log/log.txt', maxBytes=1_048_576)
    handler_1.setFormatter(formatter)
    return handler_1
