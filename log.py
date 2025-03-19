import logging.handlers
import os
import sys


def setup_log():
    os.makedirs('log', exist_ok=True)
    formatter = logging.Formatter(
        '%(levelname)s | %(asctime)s | %(filename)s\n%(message)s')
    handler_1 = logging.handlers.RotatingFileHandler('log/log.txt', maxBytes=1_048_576)
    handler_1.setFormatter(formatter)
    handler_2 = logging.StreamHandler(sys.stdout)
    handler_2.setFormatter(formatter)
    logging.basicConfig(level=logging.INFO, handlers=[handler_1, handler_2])
