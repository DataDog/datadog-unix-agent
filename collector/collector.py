# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

from collections import defaultdict
from threading import Lock
from copy import deepcopy
import logging

from . import CheckLoader, WheelLoader
from .wheel_loader import DD_WHEEL_NAMESPACE

from aggregator import Aggregator
from checks import AgentCheck
from utils.hostname import get_hostname

log = logging.getLogger(__name__)


class Collector(object):
    CORE_CHECKS = ['cpu', 'load', 'iostat', 'memory', 'filesystem', 'uptime']

    def __init__(self, config, aggregator=None):
        self._errors_mutex = Lock()
        self._config = config
        self._loaders = []
        self._check_classes = {}
        self._check_classes_errors = defaultdict(dict)
        self._check_instance_errors = defaultdict(dict)
        self._check_instances = defaultdict(list)
        self._check_instance_signatures = {}
        self._hostname = get_hostname()
        self._aggregator = aggregator

        self.set_loaders()

    def set_loaders(self):
        check_loader = CheckLoader()
        check_loader.add_place(self._config['additional_checksd'])
        self._loaders = [check_loader]
        self._loaders.append(WheelLoader(namespace=DD_WHEEL_NAMESPACE))

    def set_aggregator(self, aggregator):
        if not isinstance(aggregator, Aggregator):
            raise ValueError('argument should be of type Aggregator')

        self._aggregator = aggregator

    def collector_status(self):
        self._errors_mutex.acquire()
        try:
            loader_errors = deepcopy(self._check_classes_errors)
            runtime_errors = deepcopy(self._check_instance_errors)
        finally:
            self._errors_mutex.release()

        return loader_errors, runtime_errors

    def load_core_checks(self):
        from checks.corechecks.system import (
            Cpu,
            Load,
            Memory,
            IOStat,
            Filesystem,
            UptimeCheck
        )
        self._check_classes['cpu'] = Cpu
        self._check_classes['filesystem'] = Filesystem
        self._check_classes['iostat'] = IOStat
        self._check_classes['load'] = Load
        self._check_classes['memory'] = Memory
        self._check_classes['filesystem'] = Filesystem
        self._check_classes['uptime'] = UptimeCheck

    def load_check_classes(self):
        self.load_core_checks()

        self._errors_mutex.acquire()
        try:
            for _, check_configs in self._config.get_check_configs().items():
                for check_name in check_configs:
                    log.debug("Found config for check %s...", check_name)

                    if check_name in self._check_classes:
                        continue

                    for loader in self._loaders:
                        try:
                            check_class, errors = loader.load(check_name)
                            if check_class:
                                self._check_classes[check_name] = check_class
                            if errors:
                                self._check_classes_errors[check_name][type(loader).__name__] = errors

                            if check_class:
                                log.debug("Class found for %s...", check_name)
                                break
                        except Exception:
                            log.exception("unexpected error loading check %s", check_name)
        finally:
            self._errors_mutex.release()

    def instantiate_checks(self):
        for source, check_configs in self._config.get_check_configs().items():
            for check_name, configs in check_configs.items():
                log.debug('Trying to instantiate: %s', check_name)
                check_class = self._check_classes.get(check_name)
                if check_class:
                    for config in configs:
                        init_config = config.get('init_config', {})
                        if init_config is None:
                            init_config = {}
                        instances = config.get('instances')  # should be single instance
                        for instance in instances:
                            signature = (check_name, init_config, instance)
                            signature_hash = AgentCheck.signature_hash(*signature)
                            if signature_hash in self._check_instance_signatures:
                                log.info('instance with identical signature already configured - skipping')
                                continue

                            try:
                                check_instance = check_class(check_name, init_config, instance, self._aggregator)
                                self._check_instances[check_name].append(check_instance)
                                self._check_instance_signatures[signature_hash] = signature
                            except Exception as e:
                                log.error("unable to instantiate instance %s for %s: %s",
                                          instance, check_name, e)

        for check_name in self.CORE_CHECKS:
            if check_name in self._check_instances:
                # already instantiated - skip
                continue

            check_class = self._check_classes[check_name]
            signature = (check_name, {}, {})
            signature_hash = AgentCheck.signature_hash(*signature)
            try:
                check_instance = check_class(*signature)
                check_instance.set_aggregator(self._aggregator)
                self._check_instances[check_name] = [check_instance]
                self._check_instance_signatures[signature_hash] = signature
            except Exception:
                log.error("unable to instantiate core check %s", check_name)

    def run_checks(self):
        for name, checks in self._check_instances.items():
            log.debug('running check %s...', name)
            for check in checks:
                try:
                    result = check.run()
                except Exception:
                    log.exception("error for instance: %s", str(check.instance))

                if result:
                    self._check_instance_errors[name][check.signature] = result
                    log.error('There was an error running your %s: %s', name, result.get('message'))
                    log.error('Traceback %s: %s', name, result.get('traceback'))
