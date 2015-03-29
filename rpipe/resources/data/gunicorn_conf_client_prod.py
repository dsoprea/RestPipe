import os.path

user = 'www-data'
group = 'www-data'

debug = 'false'
daemon = 'false'

bind = 'unix:/tmp/rpclient.gunicorn.sock'

errorlog = os.path.join('/var/log/restpipe.log')
loglevel = 'warning'
worker_class = 'gevent'

timeout = 120
