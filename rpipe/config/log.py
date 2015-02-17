import sys
import os
import os.path
import logging
import logging.handlers

logger = logging.getLogger()

is_debug = bool(int(os.environ.get('DEBUG', '0')))

if is_debug is True:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)

format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
formatter = logging.Formatter(format)

ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger.addHandler(ch)

ch = logging.handlers.SysLogHandler(
        facility=logging.handlers.SysLogHandler.LOG_LOCAL0)

ch.setFormatter(formatter)
logger.addHandler(ch)
