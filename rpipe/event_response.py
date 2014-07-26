import logging

_logger = logging.getLogger(__name__)


class PipeFailError(Exception):
    def __init__(self, message, traceback, class_name, return_code):
        message = "(%d) [%s] %s" % \
                  (return_code, class_name, message)

        super(PipeFailError, self).__init__(message)

        self.__error_message = message
        self.__error_traceback = traceback
        self.__error_class_name = class_name
        self.__return_code = return_code

    @property
    def error_message(self):
        return self.__error_message

    @property
    def error_traceback(self):
        return self.__error_traceback

    @property
    def error_class_name(self):
        return self.__error_class_name

    @property
    def return_code(self):
        return self.__return_code

def raise_for_exception(r):
    return_code = int(r.headers['X-Event-Return-Code'])
    _logger.debug("Pipe event returned (%d).", return_code)

    if return_code != 0:
        error_info = r.json()
        try:
            raise PipeFailError(
                    error_info['exception']['message'], 
                    error_info['exception']['traceback'],
                    error_info['exception']['class'],
                    return_code)
        except LookupError:
            _logger.exception("Pipe exception not as expected:\n%s" % (error_info,))
            raise
