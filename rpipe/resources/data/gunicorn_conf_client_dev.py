debug = 'true'
daemon = 'false'

bind = 'unix:/tmp/rpclient.gunicorn.sock'

errorlog = '-'
loglevel = 'warning'
worker_class = 'gevent'

timeout = 300
