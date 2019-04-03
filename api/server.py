# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import asyncio
import logging
from datetime import datetime

import tornado.httpserver
import tornado.ioloop
import tornado.web
from threading import Thread

from tornado.platform.asyncio import AnyThreadEventLoopPolicy

from .handlers import (
    AgentStatusHandler,
    DogstatsdStatusHandler,
)


log = logging.getLogger(__name__)


class APIServer(Thread):

    def __init__(self, config, collector, aggregator_stats, dsd_aggregator_stats=None):
        # start API
        super(APIServer, self).__init__()

        # we'll need an event loop in the APIServer thread
        asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())

        self._config = config
        self._addr = config['api']['bind_host']
        self._port = config['api']['port']
        self._start_time = datetime.utcnow()
        self._app = tornado.web.Application([
            (r"/status", APIStatusHandler, dict(
                config=self._config,
                collector=collector,
                started=self._start_time,
                aggregator_stats=aggregator_stats)),
        ])

        self._server = tornado.httpserver.HTTPServer(self._app)

    def stop(self):
        log.info("Stopping API Server...")
        self._server.stop()
        self._ioloop.add_callback(self._ioloop.stop)

    def run(self):
        log.info("Starting API Server...")
        self._server.listen(self._port, address=self._addr)
        self._ioloop = tornado.ioloop.IOLoop.instance()
        self._ioloop.start()
