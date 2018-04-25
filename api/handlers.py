# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import logging
import tornado
import json


log = logging.getLogger(__name__)


class APIStatusHandler(tornado.web.RequestHandler):
    def initialize(self, aggregator):
        self.aggregator = aggregator

    def get(self):
        stats, count = self.aggregator.get_aggregator_stats()

        output = {'total count': count}
        for signature, values in stats.iteritems():
            check = signature[0]
            if check in output:
                output[check] += values
            else:
                output[check] = values

        self.write(json.dumps(output))
