# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import logging
import tornado
import json


log = logging.getLogger(__name__)


class APIStatusHandler(tornado.web.RequestHandler):
    def initialize(self, aggregator_stats):
        self._aggregator_stats = aggregator_stats

    def get(self):
        stats = self._aggregator_stats.get_aggregator_stats()

        check_stats = stats.pop('stats')
        stats['checks'] = {}
        for signature, values in check_stats.iteritems():
            check = signature[0]
            if check in stats['checks']:
                stats['checks'][check]['merics'] += values
            else:
                stats['checks'][check] = {'metrics': values}

        self.write(json.dumps(stats))
