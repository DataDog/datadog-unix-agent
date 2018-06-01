# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import logging
import select
import socket

from utils.network import (
    IPPROTO_IPV6,
    IPV6_V6ONLY,
    ipv6_support,
    get_socket_address,
)


class Server(object):
    """
    A statsd udp server.
    """
    UDP_SOCKET_TIMEOUT = 5

    def __init__(self, aggregator, host, port, forward_to_host=None, forward_to_port=None, so_rcvbuf=None):
        self.sockaddr = None
        self.socket = None
        self.aggregator = aggregator
        self.host = host
        self.port = port
        self.buffer_size = 1024 * 8
        self.so_rcvbuf = so_rcvbuf

        self.running = False

        self.should_forward = forward_to_host is not None

        self.forward_udp_sock = None
        # In case we want to forward every packet received to another statsd server
        if self.should_forward:
            if forward_to_port is None:
                forward_to_port = 8125

            logging.info("External statsd forwarding enabled. All packets received \
                         will be forwarded to %s:%s" % (forward_to_host, forward_to_port))
            try:
                self.forward_udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.forward_udp_sock.connect((forward_to_host, forward_to_port))
            except Exception:
                logging.exception("Error while setting up connection to external statsd server")

    def start(self):
        """
        Run the server.
        """
        ipv4_only = not ipv6_support()
        addr_family = socket.AF_INET if ipv4_only else socket.AF_INET6

        self.socket = socket.socket(addr_family, socket.SOCK_DGRAM)
        if not ipv4_only:
            # Configure the socket so that it accepts connections from both
            # IPv4 and IPv6 networks in a portable manner.
            self.socket.setsockopt(IPPROTO_IPV6, IPV6_V6ONLY, 0)

        # Set SO_RCVBUF on the socket if a specific value has been
        # configured.
        if self.so_rcvbuf is not None:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, int(self.so_rcvbuf))

        self.socket.setblocking(0)
        try:
            # let's get the sockaddr
            self.sockaddr = get_socket_address(self.host, int(self.port), ipv4_only=ipv4_only)
            self.socket.bind(self.sockaddr)
        except TypeError:
            logging.error('Unable to start Dogstatsd server loop, exiting...')
            raise
        except socket.error as e:
            logging.warn('unable to bind to socket (%s): %s', str(self.sockaddr), e)
            raise

        logging.info('Listening on socket address: %s', str(self.sockaddr))

        # Inline variables for quick look-up.
        buffer_size = self.buffer_size
        aggregator_submit = self.aggregator.submit_packets
        sock = [self.socket]
        socket_recv = self.socket.recv
        select_select = select.select
        select_error = select.error
        timeout = self.UDP_SOCKET_TIMEOUT
        should_forward = self.should_forward
        forward_udp_sock = self.forward_udp_sock

        # Run our select loop.
        self.running = True
        message = None
        while self.running:
            try:
                ready = select_select(sock, [], [], timeout)
                if ready[0]:
                    message = socket_recv(buffer_size)
                    aggregator_submit(message)

                    if should_forward:
                        forward_udp_sock.send(message)
            except select_error as se:
                # Ignore interrupted system calls from sigterm.
                errno = se[0]
                if errno != 4:
                    raise
            except (KeyboardInterrupt, SystemExit):
                break
            except Exception:
                logging.exception('Error receiving datagram `%s`', message)

    def stop(self):
        self.running = False
