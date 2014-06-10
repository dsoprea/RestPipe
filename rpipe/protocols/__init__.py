_MESSAGE_PACKAGE = 'rpipe.protocols'

MT_HEARTBEAT = 0x01
MT_EVENT     = 0x02

MT_HEARTBEAT_R = 0x80
MT_EVENT_R     = 0x81

_MESSAGE_MAP = {
    MT_HEARTBEAT: 'heartbeat_pb2.Heartbeat',
    MT_HEARTBEAT_R: 'heartbeat_pb2.HeartbeatReply',
    MT_EVENT: 'event_pb2.Event',
    MT_EVENT_R: 'event_pb2.EventReply',
}

_MESSAGE_MAP_R = dict([(v, k) for (k, v) in _MESSAGE_MAP.items()])

def get_fq_cls_name_for_type(message_type):
    return _MESSAGE_MAP[message_type]

def get_fq_module_name_for_type(message_type):
    return ('%s.%s' % (_MESSAGE_PACKAGE, _MESSAGE_MAP[message_type]))

def get_type_from_obj(message_obj):
    module_name = message_obj.__module__
    pivot = module_name.rfind('.')
    fq_cls = module_name[pivot + 1:] + '.' + message_obj.__class__.__name__
    return _MESSAGE_MAP_R[fq_cls]
