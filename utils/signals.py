# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

# stdlib
import logging
import sys

log = logging.getLogger(__name__)


class SignalHandler(object):
    """ A small helper class for pidfiles. """

    def __init__(self, components={}):
        self._components = components

    def register(self, component):
        identifier, comp = component
        if identifier in self._components:
            raise KeyError("component ({}) alredy registered".format(identifier))

        self._components[identifier] = comp

    def handle(self, signal):
        signal.signal(signal, self._signal_handler)

    def _signal_handler(self, signal, frame):
        log.info("Signal {} received: stopping...".format(signal))
        for identifier, component in self._components:
            log.info("Stopping {}".format(identifier))
            try:
                component.stop()
            except AttributeError:
                log.error("Registered component does not implement stop(): {}".format(identifier))

        log.info("Thanks for stopping by! See you!")
        sys.exit(0)
