# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import pytest

import signal
import threading
from time import sleep

class DummyComponent(object):
    def __init__(self):
        self._stopped = False

    def stop(self):
        self._stopped = True


def test_signal_registration(signal_handler):
    with pytest.raises(ValueError):
        signal_handler.handle(99)  # out of range

    signal_handler.handle(signal.SIGUSR2)
    assert(len(signal_handler._registered_signals) == 2)
    assert(len(signal_handler._original_handlers) == 2)

    with pytest.raises(ValueError):
        signal_handler.unhandle(99)  # out of range
    signal_handler.unhandle(signal.SIGUSR2)
    assert(len(signal_handler._registered_signals) == 1)
    assert(len(signal_handler._original_handlers) == 1)


def test_signal_delivery(signal_handler):
    dummy = DummyComponent()
    signal_handler.register('dummy', dummy)

    signal_handler.start()
    sleep(1)  # just enough time to get started

    signal.pthread_kill(threading.get_ident(), signal.SIGUSR1)
    sleep(1)  # signal delivery lapse

    assert(dummy._stopped)
