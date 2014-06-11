import rpipe.exceptions


class RpServerException(rpipe.exceptions.RpException):
    pass

class RpNoConnectionException(RpServerException):
    pass
