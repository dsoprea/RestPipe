----------------------
Architectural Overview
----------------------

A bidirectional pipe is established from N-clients to a central server. The 
pipes will aggressively try to remain connected (even after prolonged failure) 
and will allow all nodes to transmit events (queries) to each other via a 
local web-server on each. The pipe is SSL-encrypted and -authenticated.


--------------
Usage Overview
--------------

A request is made from a script, application, etc.. on the server or a client
node to the local RestPipe webserver. The webserver converts the REST request
to a wire-level message ('event') containing the noun, verb, post-data, and 
content-type. If the event is sent from the server, then a hostname for the
client must be included at the front of the URL path. This hostname will be
used to lookup the connection.

The message exchange of the receiving node will receive this message, and 
passed to the message-loop. The message-loop will derive a method on the
configured event-handler class to be used to handle the event. The method will
either return a 3-tuple of mime-type, return-code, and data, or just straight 
data (with a default mime-type of "application/json" and code of (0)). If the 
mime-type is JSON, the data will be encoded automatically.

The mime-type, return-code, and data will then be returned as an event back 
over the pipe. The message-exchange will receive this, see that it's a reply,
store it as such, and signal the original web-request that a reply has been
received. The reply is collected by the web-request, and then returned with
the content-type and data from the reply.


Event Handling
==============

The method on the event-handler is derived from the noun and verb from the web-
request. For example, a *GET* request is placed to the noun "time". This will
call a method named "get_time". If you were to call a noun named "time/utc",
the handler would be named "get_time_utc". The method will receive at least two
arguments: connection context information, and post-data. The "post-data" will 
be a 2-tuple of mime-type and actual data. They will both be empty strings if 
not relevant.

There is also support for arguments to be passed by URL (like with normal REST
requests, passed via URL or query parameters). The arguments are a single-
slash-delimited list of strings separated from the noun using a double-slash. 
For example, if "/cat//hello%20/world" is the path and *GET* is the verb, then
the handler will be "get_cat" and the parameters will be context, post-data, 
"hello ", and "world".


------------
Requirements
------------

Client and server nodes are functionally equivalent. The only difference are 
the following:

1. Clients establish and maintain connections
2. Clients always talk to one specific server, but in order for a server to 
   send events to a client, it has to have a hostname or IP address of that 
   client.

The general idea is that the client nodes may need access to data that's only 
accessible to the server node, and the server node might need access to 
something that's only accessible to one of the client nodes. Therefore, the 
website, backend application, or other miscellaneous processes that you have 
running on a particular node can use the local RestPipe interface to send an 
event to get what it needs. 

We recommend Nginx as a webserver to receive and forward the local requests to
RP. If a machine need not originate any requests, that instance of RP does not 
need a webserver.


----------------
Example Use-Case
----------------

A public-facing webserver needs access to the content of a file-server that 
does not allow any inbound connections. You will run RestPipe (RP) as a client 
on the file-server and RP as a server on the webserver. The RP client on the 
file-server will maintain a connection with the RP server on the webserver.

The application on the webserver will make web-requests to the RP server on
the local machine, these requests will be translated to events and sent to the
RP-client on the fileserver via the secure pipe, the event will be dispatched 
to the event-handler, the event-handler will find/read the requested file and 
return the data, the RP-server will receive the response, the web-request will 
return the response.


------------
Technologies
------------

- web.py
- gevent
- Protocol Buffers
- SSL authentication


----------------
Design Decisions
----------------

It is expected that events and their responses are reasonably sized. As the 
HTTP requests and the event responses are being translated into contiguous, 
discrete messages and sent over a socket, there are no elegant ways to handle 
large events. If you need to, than use RestPipe only as a signaling solution,
and have the handlers stage the data into a secondary location (like S3 for 
large files, if you're working with AWS).


---------------
Getting Started
---------------

This is a walkthrough of how to get an RP server and client running on a 
development machine. When it comes to moving to production, the following 
things will probably change (aside from the client and server being on separate 
machines):

- The webservers' virtualhost hostnames.
- The RP server and client webserver ports/bindings.
- The RP server socket-server port/binding.
- Use a corporate certificate authority to generate official server and client 
  identities.
- Running Gunicorn in production mode (it's started in development mode, 
  below).
- Customized event-handlers.


Establishing SSL Identities
===========================

We're going to use `CaKit <https://github.com/dsoprea/CaKit>`_ to establish 
keys and certificates. You may use any method that you prefer.

1. Extract the CaKit project in order to easily generate keys::

    $ sudo git clone https://github.com/dsoprea/CaKit.git ca_kit
    Cloning into 'ca_kit'...
    remote: Counting objects: 38, done.
    remote: Compressing objects: 100% (23/23), done.
    remote: Total 38 (delta 19), reused 31 (delta 12)
    Unpacking objects: 100% (38/38), done.
    Checking connectivity... done.

2. Build identities::

    $ cd ca_kit/
    $ sudo ./create_ca.py
    $ sudo ./create.py -n server
    $ sudo ./sign.py -n server
    $ sudo ./create.py -n client
    $ sudo ./sign.py -n client
    $ ls -1 output/
    ca.crt.pem
    ca.csr.pem
    ca.key.pem
    ca.public.pem
    client.crt.pem
    client.csr.pem
    client.key.pem
    client.public.pem
    server.crt.pem
    server.csr.pem
    server.key.pem
    server.public.pem


Configure Nginx
===============

1. Define *rpclient.local* and *rpserver.local* in your */etc/hosts* file as *127.0.0.1*.
2. Added example Nginx configs::

    upstream rp_client {
        server unix:/tmp/rpclient.gunicorn.sock fail_timeout=0;
    }

    server {
            server_name rpclient.local;
            keepalive_timeout 5;

            location /favicon.ico {
                return 404;
            }

            location / {
                proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                proxy_set_header Host $http_host;
                proxy_redirect off;

                proxy_pass http://rp_client;
            }
    }

    upstream rp_server {
        server unix:/tmp/rpserver.gunicorn.sock fail_timeout=0;
    }

    server {
            server_name rpserver.local;
            keepalive_timeout 5;

            location /favicon.ico {
                return 404;
            }

            location / {
                proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                proxy_set_header Host $http_host;
                proxy_redirect off;

                proxy_pass http://rp_server;
            }
    }


Installing RestPipe
===================

1. Install RestPipe::

    $ sudo pip install restpipe

2. Load identities::

    $ cd /usr/local/ca_kit/output/
    $ sudo rp_server_set_identity server.key.pem server.crt.pem ca.crt.pem 
    $ sudo rp_client_set_identity client.key.pem client.crt.pem

3. Start the RestPipe server::

    $ rp_server_start_gunicorn_dev 

4. Start the RestPipe client (in another window)::

    $ rp_client_start_gunicorn_dev 

The server and the client can actually be started in any order. Also, just as
the scripts above are meant to development (notice the "dev" suffix), there are
production versions as well.

At this point, you have a pipe between a single server and a single client. 
There's not a whole lot of verbosity by default, but you can see the 
underlying mechanics if the environment variable "DEBUG" is set to "1".


Example Events
==============

Obviously, you're responsible for implementing any event-handlers that you 
might need. However, there are two event handlers defined by default, as an
example, on both the server side and client side. The commands and responses
below correlate to the example Nginx configs, above.

- *time* (*GET*)

  From client::

    $ curl http://rpclient.local/server/time && echo
    {"time_from_server": 1402897823.882672}

  From server::

    $ curl http://rpserver.local/client/localhost/time && echo
    {"time_from_client": 1402897843.879908}

- *cat* (*GET*)

  From client:: 

    $ curl http://rpclient.local/server/cat//hello%20/world && echo
    {"result_from_server": "hello world"}

  From server::

    $ curl http://rpserver.local/client/localhost/cat//hello%20/world && echo
    {"result_from_client": "hello world"}


-------------
Customization
-------------

To set the server hostname and port for the client, set the 
`RP_CLIENT_TARGET_HOSTNAME` and `RP_CLIENT_TARGET_PORT` environment variables.

The set the interface binding on the server, set the *BIND_IP* and *BIND_PORT*
environment variables.

When you're ready to implement your own event-handler, start your own project, 
write your module, make sure it inherits properly, and set the right 
environment variable with the fully-qualified name of your module.

If you're writing a server event-handler, make sure it inherits from 
*rpipe.server.connection.ServerEventHandler*, and set the fully-qualified module 
name as the `RP_EVENT_HANDLER_FQ_CLASS` environment variable. If you're writing a 
client event-handler, use the *ClientEventHandle* class from the same package 
and the `RP_EVENT_HANDLER_FQ_CLASS` environment variable.

Many of the configurables can be overriden via environment variables. If you 
need to override more than a handful of values, you might prefer to set any 
number of values in your own module, and then set the fully-qualified name of 
the module into the `RP_CLIENT_USER_CONFIG_MODULE` or 
`RP_SERVER_USER_CONFIG_MODULE` environment variable(s). All of the values from 
your module will overwrite the defaults.

You may also inherit from `rpipe.connection_state_events.ConnectionStateEvents`
and override the `connection_success` and `connection_fail` methods.


--------------
Error Handling
--------------

When an uncaught exception occurs on the side of the pipe that is handling an 
event, it will be captured and forwarded via the HTTP body with a non-zero 
return-code (which is set into the `X-Event-Return-Code` response header)::

    {
        "exception": {
            "message": "<message>",
            "traceback": "<traceback>",
            "class": "<class>",
        }
    }

If you're using the `requests <http://docs.python-requests.org/en/latest/>`_ 
client, you can call `rpipe.event_response.raise_for_exception` with the 
response, and, if there was an error, it'll build a PipeFailError exception 
with the information from the response and raise it.


----------
Statistics
----------

RestPipe will emit `statsd <https://github.com/etsy/statsd/>`_ events to 
*localhost:8125* by default. To override this, set the `RP_STATSD_HOST` and
`RP_STATSD_PORT` environment variables. To disable this, set them to empty.
