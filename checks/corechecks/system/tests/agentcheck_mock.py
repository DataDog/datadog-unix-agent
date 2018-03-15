import logging

from collections import defaultdict


class AgentCheckTest(object):
    def __init__(self, name, init_config, instance):
        self.metrics = defaultdict(list)
        self.events = []
        self.service_checks = []
        self.name = name
        self.log = logging.getLogger('%s.%s' % (__name__, self.name))

    def gauge(self, name, value, tags=None):
        self.metrics[name].append({"type": "gauge", "value": value, "tags": tags})

    def count(self, name, value, tags=None):
        self.metrics[name].append({"type": "count", "value": value, "tags": tags})

    def monotonic_count(self, name, value, tags=None):
        self.metrics[name].append({"type": "monotonic_count", "value": value, "tags": tags})

    def rate(self, name, value, tags=None):
        self.metrics[name].append({"type": "rate", "value": value, "tags": tags})

    def histogram(self, name, value, tags=None):
        self.metrics[name].append({"type": "histogram", "value": value, "tags": tags})

    def historate(self, name, value, tags=None):
        self.metrics[name].append({"type": "historate", "value": value, "tags": tags})

    def get_metrics(self):
        return dict(self.metrics)

    def service_check(self, name, status, tags=None, message=None):
        self.service_checks.append({"name": name, "status": status, "tags": tags, "message": message})

    def event(self, event):
        self.events.append(event)
