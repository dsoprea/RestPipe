class StateChangeEvent(object):
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
