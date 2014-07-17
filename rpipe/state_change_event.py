class StateChangeEvent(object):
    def connect_success(self):
        """Invoked after a connection is established."""

        pass

    def connect_fail(self):
        """Invoked after a connection fails or is broken."""

        pass
