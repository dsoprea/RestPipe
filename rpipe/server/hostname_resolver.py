import socket


class HostnameResolver(object):
    def lookup(self, hostname):
        raise NotImplementedError()


class HostnameResolverDns(HostnameResolver):
    """This is a mechanism to derive IPs from hostnames when routing events 
    from the server to a particular client.
    """

    def lookup(self, hostname):
        try:
            return socket.gethostbyname(hostname)
        except socket.gaierror as e:
            message = str(e)
            if 'not known' in message:
                raise LookupError("Hostname [%s] not resolvable." % (hostname))

            raise
