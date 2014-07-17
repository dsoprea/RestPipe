import rpipe.config.exchange


class RpException(Exception):
    pass


class RpClientException(RpException):
    pass


class RpClientReconnectException(RpClientException):
    pass


class RpConnectionRetry(RpException):
    pass


class RpConnectionFail(RpConnectionRetry):
    pass


class RpConnectionClosed(RpConnectionRetry):
    pass
