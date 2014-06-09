#!/usr/bin/env python2.7

import os.path
import logging

import gevent
import gevent.server
import gevent.ssl

import rpipe.config.server

_logger = logging.getLogger(__name__)


class ConnectionHandlerBaseClass(object):
    def handle(socket, address):
        raise NotImplementedError()


class DefaultConnectionHandler(ConnectionHandlerBaseClass):
    def handle(self, socket, address):
        print("Connection: %s" % (address,))

        fileobj = socket.makefile()

        fileobj.write("Hello!")
        fileobj.flush()

        for line in fileobj:
            print("Read: %s" % (line,))


def _load_cls_from_string(fq_cls_name):
    pivot = fq_cls_name.rfind('.')
    cls_name = fq_cls_name[pivot+1:]
    m = __import__(fq_cls_name[:pivot], fromlist=[cls_name])
    return getattr(m, cls_name)


class Server(object):
    def __init__(self):
        fq_cls_name = rpipe.config.server.CONNECTION_HANDLER_CLASS
        self.__handler = _load_cls_from_string(fq_cls_name)()

    def run(self):
        binding = (rpipe.config.server.BIND_HOSTNAME, 
                   rpipe.config.server.BIND_PORT)

        _logger.info("Running server: %s", binding)

        server = gevent.server.StreamServer(
                    binding, 
                    self.__handler.handle, 
                    cert_reqs=gevent.ssl.CERT_REQUIRED,
                    keyfile=rpipe.config.server.KEY_FILEPATH,
                    certfile=rpipe.config.server.CRT_FILEPATH,
                    ca_certs=rpipe.config.server.CA_CRT_FILEPATH)

        server.serve_forever()
