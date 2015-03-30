#
# Copyright (C) 2015 OpenPeak Inc.
# All rights reserved
#
user = 'www-data'
group = 'www-data'

debug = 'false'
daemon = 'true'

bind = 'unix:/tmp/rpclient.gunicorn.sock'

errorlog = '-'
loglevel = 'warning'
worker_class = 'gevent'

timeout = 120
