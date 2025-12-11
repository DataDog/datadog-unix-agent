# checks/corechecks/net/network/network.py
# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

# 3p
import psutil

from checks import AgentCheck


class NetworkCheck(AgentCheck):
    """
    Corecheck version of the bundled Network integration.
    Behavior is identical to the original datadog_checks.network.Network.
    """

    METRIC_NET = 'system.net.{}'
    ATTR_MAP = {
        'bytes_sent': 'bytes_sent',
        'bytes_recv': 'bytes_rcvd',
        'packets_sent': 'packets_in.count',
        'packets_recv': 'packets_out.count',
        'errin': 'packets_in.error',
        'errout': 'packets_out.error',
        'dropin': 'packets_in.drop',
        'dropout': 'packets_out.drop',
    }

    def __init__(self, name, init_config, instance, aggregator=None):
        super(NetworkCheck, self).__init__(name, init_config, instance, aggregator)

        self._device_whitelist = instance.get('device_whitelist', [])
        self._device_blacklist = instance.get('device_blacklist', [])
        self._custom_tags = instance.get('tags', [])

    def check(self, instance):
        counters = psutil.net_io_counters(pernic=True)

        for device, counter in counters.items():
            if self._exclude_device(device):
                continue
            self._collect_metrics(device, counter)

    def _collect_metrics(self, device, counter):
        metric_tags = [] if self._custom_tags is None else self._custom_tags[:]
        metric_tags.append("device:{}".format(device))

        for attr, metric in self.ATTR_MAP.items():
            try:
                value = getattr(counter, attr)
                # Rate submission (delta computed by Agent)
                self.rate(self.METRIC_NET.format(metric), value, tags=metric_tags)
            except AttributeError as e:
                # Some OS may not have all counters
                self.log.debug(
                    'Network metric {} not collected for {}: {}'.format(attr, device, e)
                )

    def _exclude_device(self, device):
        if device in self._device_blacklist:
            return True
        if self._device_whitelist and device not in self._device_whitelist:
            return True
        return False
