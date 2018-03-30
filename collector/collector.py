# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

from collections import defaultdict
import logging

from . import CheckLoader, WheelLoader
from .wheel_loader import DD_WHEEL_NAMESPACE

from aggregator import Aggregator
from utils.hostname import get_hostname

log = logging.getLogger(__name__)


class Collector(object):

    def __init__(self, config, aggregator=None):
        self._config = config
        self._loaders = []
        self._check_classes = {}
        self._check_classes_errors = {}
        self._check_instances = defaultdict(list)
        self._check_instance_signatures = set()
        self._hostname = get_hostname()
        self._aggregator = aggregator

        self.set_loaders()

    def set_loaders(self):
        self._loaders = [WheelLoader(namespace=DD_WHEEL_NAMESPACE)]
        check_loader = CheckLoader()
        check_loader.add_place(self._config['additional_checksd'])
        self._loaders.append(check_loader)

    def set_aggregator(self, aggregator):
        if not isinstance(aggregator, Aggregator):
            raise ValueError('argument should be of type Aggregator')

        self._aggregator = aggregator

    def load_check_classes(self):
        for _, check_configs in self._config.get_check_configs().iteritems():
            for check_name in check_configs:
                if check_name in self._check_classes:
                    continue

                for loader in self._loaders:
                    try:
                        check_class, errors = loader.load(check_name)
                        if check_class:
                            self._check_classes[check_name] = check_class
                        if errors:
                            self._check_classes_errors[check_name] = errors
                    except Exception:
                        log.exception("unexpected error loading check %s", check_name)

    def instantiate_checks(self):
        for source, check_configs in self._config.get_check_configs().iteritems():
            for check_name, configs in check_configs.iteritems().iteritems():
                check_class = self._check_classes.get(check_name)
                if check_class:
                    for config in configs:
                        init_config = config.get('init_config', {})
                        instances = config.get('instances')  # should be single instance
                        for instance in instances:
                            signature = (init_config, instance)
                            if signature in self._check_instance_signatures:
                                continue

                            try:
                                check_instance = check_class(check_name, init_config, instance)
                                check_instance.set_aggregator(self._aggregator)
                                self._check_instances[check_name].append(check_instance)
                                self._check_instance_signatures.add(signature)
                            except Exception:
                                log.error("unable to instantiate instance %s for %s",
                                        instance, check_name)

    def run_checks(self):
        for name, checks in self._check_instances.iteritems():
            self.log.debug('running check %s...', name)
            for check in checks:
                try:
                    check.run(check.instance)
                except Exception:
                    log.exception("error for instance: %s", str(check.instance))
