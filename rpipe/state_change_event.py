class ClientStateChangeEvent(object):
    def connect_success(self, retry_attempts, last_connection_dt):
        """Invoked after a connection is established.
        
        `retry_attempts` reflects how many failures we encountered before this
        connection.
        """

        pass

    def connect_fail(self, retry_attempts, last_connection_dt):
        """Invoked after a connection fails or is broken.

        `retry_attempts` reflects how many failures we've encountered before we 
        were successful.
        """

        pass


class ServerStateChangeEvent(object):
    def idle(self, waiting_since_dt, duration_s):
        """Triggered every minute while no connections are present."""

        pass

    def connection_added(self, ip, new_count):
        """A new connection has been established."""

        pass

    def connection_removed(self, ip, new_count):
        """A connection has been lost."""

        pass
