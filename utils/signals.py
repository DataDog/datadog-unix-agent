# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

# stdlib
import logging
import fcntl
import os
import sys
import select
import signal
from threading import Thread, Event

from collections import OrderedDict

log = logging.getLogger(__name__)


class SignalHandler(Thread):
    """ A handler class for more reliable signal delivery."""

    def __init__(self, components={}):
        super(SignalHandler, self).__init__()

        wakeup_r, wakeup_w = os.pipe()
        fcntl.fcntl(wakeup_w, fcntl.F_SETFL, os.O_NONBLOCK)
        self._wakeup_r = wakeup_r
        self._wakeup_w = wakeup_w
        # we don't care about order for initial components, if any
        self._components = OrderedDict(components)
        self._registered_signals = set()
        self._stop_flag = Event()  # TODO: use events

        signal.set_wakeup_fd(self._wakeup_w)

    def register(self, component):
        identifier, comp = component
        if identifier in self._components:
            raise KeyError("component ({}) alredy registered".format(identifier))

        self._components[identifier] = comp

    def handle(self, signum):
        self._registered_signals.add(signum)
        # we handle the signals when we read them from the
        # the pipe.
        signal.signal(signum, self._dummy_handler)

    def run(self):
        self.listen()

    def stop(self):
        self._stop_flag.set()
        os.close(self._wakeup_w)
        os.close(self._wakeup_r)

    def listen(self):
        while not self._stop_flag.is_set():
            delivered = False
            readable, _, _ = select.select([self._wakeup_r], [], [], 1)
            for fp in readable:
                signum = int.from_bytes(os.read(fp, 1), byteorder='big')
                if signum not in self._registered_signals:
                    continue

                log.debug("Signal delivered: {}".format(signum))

                self._signal_handler(signum, None)
                delivered = True

            if delivered:
                self.stop()

    def _dummy_handler(self, signal, frame):
        pass

    def _signal_handler(self, signal, frame):
        log.info("Signal {} received: stopping...".format(signal))
        for identifier, component in self._components.items():
            log.info("Stopping {}".format(identifier))
            try:
                component.stop()
            except AttributeError:
                log.error("Registered component does not implement stop(): {}".format(identifier))
