import rpipe.config.exchange


class RpException(Exception):
    pass


class RpClientException(RpException):
    pass


class RpClientReconnectException(RpClientException):
    pass


class RpHandleException(RpException):
    def __init__(self, code, *args, **kwargs):
        super(RpHandleException, self).__init__(*args, **kwargs)
        self.__code = code

    @property
    def code(self):
        return self.__code


class RpHandleError(RpHandleException):
    def __init__(self, code=rpipe.config.exchange.UNHANDLED_EVENT_CODE, *args, 
                 **kwargs):
        super(RpHandleError, self).__init__(code, *args, **kwargs)


class RpConnectionRetry(RpException):
    pass


class RpConnectionFail(RpConnectionRetry):
    pass


class RpConnectionClosed(RpConnectionRetry):
    pass
