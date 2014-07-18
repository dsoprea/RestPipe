import logging
import contextlib

import statsd

import rpipe.config.statsd

_logger = logging.getLogger(__name__)


if rpipe.config.statsd.STATSD_HOSTNAME or \
   rpipe.config.statsd.STATSD_PORT:
    if bool(rpipe.config.statsd.STATSD_HOSTNAME) ^ \
       bool(rpipe.config.statsd.STATSD_PORT):
        raise EnvironmentError("The statsd hostname and port must both be "
                               "empty or both be set.")

    _SC = statsd.StatsClient(
            rpipe.config.statsd.STATSD_HOSTNAME, 
            rpipe.config.statsd.STATSD_PORT)
else:
    _SC = None

def post_to_counter(event):
    if _SC is None:
        return

    _logger.debug("Incrementing: [%s]", event)
    _SC.incr(event)

@contextlib.contextmanager
def time_and_post(timing_event, success_event=None, fail_event=None):
    if _SC is None:
        return

    t = _SC.timer(timing_event)
    t.start()

    try:
        yield
    except:
        if fail_event is not None:
            _logger.debug("Incrementing counter for FAILED timed event: [%s]", fail_event)
            post_to_counter(fail_event)

        raise
    else:
        if success_event is not None:
            _logger.debug("Incrementing counter for SUCCESSFUL timed event: [%s]", success_event)
            post_to_counter(success_event)

    _logger.debug("Posting timing for complete event: [%s]", timing_event)
    t.stop()
