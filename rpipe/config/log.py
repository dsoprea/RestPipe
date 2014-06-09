import logging
import os

logger = logging.getLogger()

#is_debug = bool(int(os.environ.get('DEBUG', '0')))
is_debug = True

if is_debug is True:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.WARN)

ch = logging.StreamHandler()

FMT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
formatter = logging.Formatter(FMT)
ch.setFormatter(formatter)
logger.addHandler(ch)
