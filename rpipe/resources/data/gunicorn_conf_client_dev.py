debug = 'true'
daemon = 'false'

bind = 'unix:/tmp/rp_client.gunicorn.sock'

errorlog = '-'
loglevel = 'debug'
worker_class = 'gevent'
