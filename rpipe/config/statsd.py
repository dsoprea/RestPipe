import os

STATSD_HOSTNAME = os.environ.get('RP_STATSD_HOST', 'localhost')
STATSD_PORT = int(os.environ.get('RP_STATSD_PORT', '8125'))

EVENT_CONNECTION_CLIENT_NEW_TICK               = 'client.connect.new.tick'
EVENT_CONNECTION_CLIENT_NEW_ATTEMPT_TIMING     = 'client.connect.new.attempt.timing'
EVENT_CONNECTION_CLIENT_CONNECTED_TICK         = 'client.connect.connected.tick'
EVENT_CONNECTION_CLIENT_BROKEN_TICK            = 'client.connect.broken.tick'
EVENT_CONNECTION_CLIENT_HEARTBEAT_TIMING       = 'client.connect.heartbeat.timing'
EVENT_CONNECTION_CLIENT_HEARTBEAT_SUCCESS_TICK = 'client.connect.heartbeat.success.tick'
EVENT_CONNECTION_CLIENT_HEARTBEAT_FAIL_TICK    = 'client.connect.heartbeat.fail.tick'

EVENT_CONNECTION_SEND_TICK   = 'message.send.tick'
EVENT_CONNECTION_SEND_TIMING = 'message.send.timing'

EVENT_MESSAGE_RECEIVE_TICK          = 'message.receive.tick'
EVENT_MESSAGE_RECEIVE_HANDLE_TIMING = 'message.receive.handle.timing'

EVENT_HANDLER_TICK_TEMPLATE = 'message.received.handle.%(handler_name)s.tick'
EVENT_HANDLER_TIMING_TEMPLATE = 'message.received.handle.%(handler_name)s.timing'
