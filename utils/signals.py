# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

# stdlib
import logging
import fcntl
import os
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
        self._original_handlers = {}
        self._registered_signals = set()
        self._stop_flag = Event()
        self._stop_flag.set()

        signal.set_wakeup_fd(self._wakeup_w)

    def register(self, identifier, component):
        if identifier in self._components:
            raise KeyError("component ({}) alredy registered".format(identifier))

        self._components[identifier] = component

    def unregister(self, identifier):
        if not self._stop_flag.is_set():
            raise Exception('cannot unregister component if manager is running')

        self._components.pop(identifier)

    def handle(self, signum):
        if signum not in list(range(1, signal.NSIG)):
            raise ValueError('Invalid signal specified')

        self._registered_signals.add(signum)
        self._original_handlers[signum] = signal.getsignal(signum)

        # we actually handle the signals when we read them from
        # the pipe - hence the dummy handler.
        signal.signal(signum, self._dummy_handler)

    def unhandle(self, signum):
        if not self._stop_flag.is_set():
            raise Exception('cannot unregister handler if manager is running')
        if signum not in list(range(1, signal.NSIG)):
            raise ValueError('Invalid signal specified')

        original_handler = self._original_handlers.pop(signum)
        signal.signal(signum, original_handler)
        self._registered_signals.remove(signum)

    def run(self):
        self._stop_flag.clear()
        self.listen()

    def running(self):
        return not self._stop_flag.is_set()

    def stop(self):
        self._stop_flag.set()
        os.close(self._wakeup_w)
        os.close(self._wakeup_r)

    def listen(self):
        while not self._stop_flag.is_set():
            try:
                readable, _, _ = select.select([self._wakeup_r], [], [], 1)
                for fp in readable:
                    signum = int.from_bytes(os.read(fp, 1), byteorder='big')
                    if signum not in self._registered_signals:
                        continue

                    self._signal_handler(signum, None)
            except OSError:
                # file descriptor closed we're about to end loop
                pass

    def _dummy_handler(self, signal, frame):
        pass

    def _signal_handler(self, signal, frame):
        log.debug("Signal {} received".format(signal))
        for identifier, component in self._components.items():
            log.info("Stopping {}".format(identifier))
            try:
                component.stop()
            except AttributeError:
                log.error("Registered component does not implement stop(): {}".format(identifier))
