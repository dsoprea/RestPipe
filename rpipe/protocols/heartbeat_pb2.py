# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: heartbeat.proto

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)




DESCRIPTOR = _descriptor.FileDescriptor(
  name='heartbeat.proto',
  package='rpipe.support',
  serialized_pb='\n\x0fheartbeat.proto\x12\rrpipe.support\"\x1c\n\tHeartbeat\x12\x0f\n\x07version\x18\x01 \x02(\r\"!\n\x0eHeartbeatReply\x12\x0f\n\x07version\x18\x01 \x02(\r')




_HEARTBEAT = _descriptor.Descriptor(
  name='Heartbeat',
  full_name='rpipe.support.Heartbeat',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='version', full_name='rpipe.support.Heartbeat.version', index=0,
      number=1, type=13, cpp_type=3, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=34,
  serialized_end=62,
)


_HEARTBEATREPLY = _descriptor.Descriptor(
  name='HeartbeatReply',
  full_name='rpipe.support.HeartbeatReply',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='version', full_name='rpipe.support.HeartbeatReply.version', index=0,
      number=1, type=13, cpp_type=3, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=64,
  serialized_end=97,
)

DESCRIPTOR.message_types_by_name['Heartbeat'] = _HEARTBEAT
DESCRIPTOR.message_types_by_name['HeartbeatReply'] = _HEARTBEATREPLY

class Heartbeat(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _HEARTBEAT

  # @@protoc_insertion_point(class_scope:rpipe.support.Heartbeat)

class HeartbeatReply(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _HEARTBEATREPLY

  # @@protoc_insertion_point(class_scope:rpipe.support.HeartbeatReply)


# @@protoc_insertion_point(module_scope)
