**This documentation will still being developed.**


Overview
--------

A bidirectional pipe is established from N-clients to a central server. The 
pipes will aggressively try to remain connected (even after prolonged failure) 
and will allow all nodes to transmit events (queries) to each other via a 
local web-server on each. The pipe is SSL-encrypted and -authenticated.


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


Example Use-Case
----------------

A public-facing webserver needs access to the content of a file-server that 
does not allow any inbound connections, you might run RestPipe (RP) as a client 
on the file-server and as a server on the webserver. The RP client on the file-
server will maintain a connection with the RP server on the webserver.

When the web application needs to contact the fileserver:

1. It will make REST requests to the RP-client's local webserver (passing the 
   client hostname, even though there's only one client in this example).
2. Those requests are translated into events that get transmitted over the 
   corresponding socket connection for that client node.
3. The events are collected by the "message exchange" green-thread.
4. Each event is matched to a handler method based on the noun and verb of the 
   original REST request.
5. The event is handled in a separate green-thread.
6. The result is returned by the handler, and sent as a reply event to the RP-
   server on the webserver.
7. The data, code, and mime-type (or any exception that occured) is returned as 
   the result of the original REST request.


Technologies
------------

- web.py
- gevent
- Protocol Buffers
- SSL authentication


Design Decisions
----------------

It is expected that events and their responses are reasonably sized. As the 
HTTP requests and the event responses are being translated into contiguous, 
discrete messages and sent over a socket, there are no elegant ways to handle 
large events. If you need to, than use RestPipe only as a signaling solution,
and have the handlers stage the data into a secondary location (like S3 for 
large files, if you're working with AWS).


Getting Started
---------------

### Establishing SSL Identities

```
/usr/local$ sudo git clone https://github.com/dsoprea/CaKit.git ca_kit
Cloning into 'ca_kit'...
remote: Counting objects: 38, done.
remote: Compressing objects: 100% (23/23), done.
remote: Total 38 (delta 19), reused 31 (delta 12)
Unpacking objects: 100% (38/38), done.
Checking connectivity... done.

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
```

### Installing

```
$ sudo pip install virtualenv
$ cd /usr/local
$ sudo su
$ mkdir restpipe
$ cd restpipe
$ virtualenv .
$ source bin/activate
$ pip install restpipe


$ cd /usr/local/ca_kit/output/
$ sudo rp_server_set_identity server.key.pem server.crt.pem ca.crt.pem 
$ sudo rp_client_set_identity client.key.pem client.crt.pem
```
