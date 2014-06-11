import logging
import functools
import web

import rpipe.event
import rpipe.server.connection
import rpipe.utility
import rpipe.server.hostname_resolver

_logger = logging.getLogger(__name__)


class EventServer(object):
    def __init__(self, *args, **kwargs):
        super(EventServer, self).__init__(*args, **kwargs)

        self.__cc = rpipe.server.connection.get_connection_catalog()

        hostname_resolver_cls = rpipe.utility.load_cls_from_string(
                                   rpipe.config.server.\
                                        CLIENT_HOSTNAME_RESOLVER_CLS)

        assert issubclass(
                hostname_resolver_cls, 
                rpipe.server.hostname_resolver.HostnameResolver)

        self.__resolver = hostname_resolver_cls()

    def handle(self, hostname, verb, noun):
        _logger.info("Server received request, to be sent to client [%s]: "
                     "[%s] [%s]", hostname, verb, noun)

        try:
            ip = self.__resolver.lookup(hostname)
        except LookupError:
            raise web.HTTPError('404 Hostname not resolvable')
        except:
            _logger.exception("Could not resolve hostname: [%s]", 
                              hostname)
            raise web.HTTPError('500 Hostname resolution error')

        try:
            c = self.__cc.wait_for_connection(ip)
        except rpipe.server.connection.RpNoConnectionException:
            raise web.HTTPError('503 Client connection unavailable')            

        return rpipe.event.emit(c, verb, noun, web.data())

    def GET(self, path):
        return self.handle('get', path)

    def POST(self, path):
        return self.handle('post', path)

    def PUT(self, path):
        return self.handle('put', path)

    def DELETE(self, path):
        return self.handle('delete', path)

    def PATCH(self, path):
        return self.handle('patch', path)
