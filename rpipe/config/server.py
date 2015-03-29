import os
import os.path
import sys

USER_CONFIG_MODULE_NAME = os.environ.get('RP_SERVER_USER_CONFIG_MODULE', '')

BIND_IP = os.environ.get('RP_SERVER_BIND_INTERFACE', '0.0.0.0')
BIND_PORT = int(os.environ.get('RP_SERVER_BIND_PORT', '1234'))

_CERT_PATH = os.environ.get('RP_SERVER_CERT_PATH', '/var/lib/restpipe')

if os.path.exists(_CERT_PATH) is False:
    os.mkdir(_CERT_PATH)

_KEY_FILENAME = os.environ.get('RP_SERVER_KEY_FILENAME', 'restpipe.server.key.pem')
_CRT_FILENAME = os.environ.get('RP_SERVER_CRT_FILENAME', 'restpipe.server.crt.pem')
_CA_CRT_FILENAME = os.environ.get('RP_CA_CRT_FILENAME', 'ca.crt.pem')

KEY_FILEPATH = os.path.join(_CERT_PATH, _KEY_FILENAME)
CRT_FILEPATH = os.path.join(_CERT_PATH, _CRT_FILENAME)
CA_CRT_FILEPATH = os.path.join(_CERT_PATH, _CA_CRT_FILENAME)

DEFAULT_READ_CHUNK_LENGTH = 1024

EVENT_HANDLER_FQ_CLASS = \
    os.environ.get(
        'RP_EVENT_HANDLER_FQ_CLASS',
        'rpipe.server.connection.TestServerEventHandler')

CONNECTION_STATE_CHANGE_EVENT_CLASS = \
    os.environ.get(
        'RP_SERVER_CONNECTION_STATE_CHANGE_EVENT_CLASS',
        'rpipe.state_change_event.ServerStateChangeEvent')

DEFAULT_CONNECTION_WAIT_TIMEOUT_S = 20

CLIENT_HOSTNAME_RESOLVER_CLS = 'rpipe.server.hostname_resolver.HostnameResolverDns'

# Install attributes on this module from the optional user-config.
if USER_CONFIG_MODULE_NAME != '':
    _MODULE = sys.modules[__name__]

    _UM = __import__(USER_CONFIG_MODULE_NAME)

    for key in dir(_UM):
        if key[0] != '_':
            setattr(_MODULE, key, getattr(_UM, key))
