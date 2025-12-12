# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import time
from collections import defaultdict
from copy import copy, deepcopy
import logging

from . import CheckLoader, WheelLoader, CoreCheckLoader
from .wheel_loader import DD_WHEEL_NAMESPACE

from aggregator import Aggregator
from checks import AgentCheck
from utils.hostname import get_hostname
from utils.stats import Stats

log = logging.getLogger(__name__)


class Collector(object):

    def __init__(self, config, aggregator=None):
        self._config = config
        self._loaders = []
        self._check_classes = {}
        self._check_classes_errors = defaultdict(dict)
        self._check_instance_errors = defaultdict(dict)
        self._check_instances = defaultdict(list)
        self._check_instance_signatures = {}
        self._hostname = get_hostname()
        self._aggregator = aggregator
        self._status = Stats()

        self.set_loaders()

    def set_loaders(self):
        check_loader = CheckLoader()
        check_loader.add_place(self._config['additional_checksd'])

        core_loader = CoreCheckLoader()

        self._loaders = [
            core_loader,                 # core checks first
            check_loader,                # checks.d next
            WheelLoader(namespace=DD_WHEEL_NAMESPACE),  # bundled integrations last
        ]

    def set_aggregator(self, aggregator):
        if not isinstance(aggregator, Aggregator):
            raise ValueError('argument should be of type Aggregator')

        self._aggregator = aggregator

    @property
    def status(self):
        return self._status

    def load_check_classes(self):

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

        self._status.set_info('check_classes', copy(self._check_classes))  # shallow copy suffices
        self._status.set_info('loader_errors', deepcopy(self._check_classes_errors))

    def instantiate_checks(self):
        global_min_interval = int(self._config.get('min_collection_interval', 15))

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
                        # Convert any None values to empty dicts
                        instances = [i if isinstance(i, dict) else {} for i in instances]
                        for instance in instances:
                            signature = (check_name, init_config, instance)
                            signature_hash = AgentCheck.signature_hash(*signature)
                            if signature_hash in self._check_instance_signatures:
                                log.info('instance with identical signature already configured - skipping')
                                continue

                            try:
                                check_instance = check_class(check_name, init_config, instance, self._aggregator)

                                # Determine min_collection_interval
                                interval = (
                                    instance.get('min_collection_interval')
                                    or init_config.get('min_collection_interval')
                                    or getattr(check_class, 'DEFAULT_MIN_COLLECTION_INTERVAL', 15)
                                )

                                # Type safety + fallback
                                try:
                                    interval = int(float(interval))
                                except (TypeError, ValueError):
                                    log.warning(
                                        "Invalid min_collection_interval=%r for %s; falling back to init_config/class/global default",
                                        interval, check_name
                                    )

                                    # Retry with init_config
                                    fallback = init_config.get('min_collection_interval')
                                    try:
                                        interval = int(float(fallback))
                                    except (TypeError, ValueError):
                                        # Retry with class default
                                        fallback = getattr(check_class, 'DEFAULT_MIN_COLLECTION_INTERVAL', 15)
                                        try:
                                            interval = int(float(fallback))
                                        except (TypeError, ValueError):
                                            # Final fallback to global
                                            interval = global_min_interval

                                # Clamp interval between 1s and the global minimum
                                clamped_interval = max(interval, 1, global_min_interval)

                                if clamped_interval != interval:
                                    if interval < 1:
                                        log.warning(
                                            "min_collection_interval=%r too low for %s; clamped to global minimum=%ss",
                                            interval, check_name, global_min_interval
                                        )
                                    elif interval < global_min_interval:
                                        log.debug(
                                            "%s min_collection_interval=%s raised to global minimum=%s",
                                            check_name, interval, global_min_interval
                                        )
                                    interval = clamped_interval

                                check_instance.min_collection_interval = interval

                                # Initialize runtime tracking
                                check_instance._last_run_time = 0

                                # Register instance
                                self._check_instances[check_name].append(check_instance)
                                self._check_instance_signatures[signature_hash] = signature
                            except Exception as e:
                                log.error("unable to instantiate instance %s for %s: %s",
                                          instance, check_name, e)


    def run_checks(self):
        for name, checks in self._check_instances.items():
            log.info('running check %s...', name)
            for check in checks:
                now = time.monotonic()

                # If the check has a collection interval defined, enforce it
                if hasattr(check, 'min_collection_interval'):
                    elapsed = now - getattr(check, '_last_run_time', 0)
                    if elapsed < check.min_collection_interval:
                        log.info(
                            'Skipping %s: only %.2fs elapsed (interval %.2fs)',
                            name, elapsed, check.min_collection_interval
                        )
                        continue  # skip execution

                try:
                    result = check.run()
                    check._last_run_time = now  # update after successful run
                except Exception:
                    log.exception("error for instance: %s", str(check.instance))

                if result:
                    self._check_instance_errors[name][check.signature] = result
                    log.error('There was an error running your %s: %s', name, result.get('message'))
                    log.error('Traceback %s: %s', name, result.get('traceback'))

        self._status.set_info('runtime_errors', deepcopy(self._check_instance_errors))
