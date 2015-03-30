import os
import logging
import logging.handlers

def _configure_logs():
    logger = logging.getLogger()

    is_debug = bool(int(os.environ.get('DEBUG', '0')))

    if is_debug is True:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # Configure screen.

    format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(format)

    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    logger.addHandler(sh)

    # Configure Syslog.
    if os.path.exists('/dev/log') is True:
        format = '%(name)s - %(levelname)s - %(message)s'
        formatter = logging.Formatter(format)

        sh2 = logging.handlers.SysLogHandler(
                address='/dev/log',
                facility=logging.handlers.SysLogHandler.LOG_LOCAL1)

        sh2.setFormatter(formatter)
        logger.addHandler(sh2)

_configure_logs()
