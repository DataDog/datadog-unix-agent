# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

from collections import defaultdict
import time
import logging

from config.providers import ConfigProvider
from . import CheckLoader, WheelLoader
from .wheel_loader import DD_WHEEL_NAMESPACE

from metadata import get_metadata
from utils.hostname import get_hostname

log = logging.getLogger(__name__)


class Collector(object):

    def __init__(self, config):
        self._config = config
        self._providers = {}
        self._loaders = []
        self._check_configs = defaultdict(dict)
        self._check_classes = {}
        self._check_classes_errors = {}
        self._check_instances = defaultdict(list)
        self._check_instance_signatures = set()
        self._hostname = get_hostname()
        self._metadata = {
            'host_metadata': {
                'last': time.time(),
                'interval': int(config.get('metadata_interval')),
                'meta': None,
            },
        }

        self.set_loaders()

    def set_loaders(self):
        self._loaders.append(WheelLoader(namespace=DD_WHEEL_NAMESPACE))
        check_loader = CheckLoader()
        check_loader.add_place(self._config['additional_checksd'])
        self._loaders.append(check_loader)

    def add_provider(self, id, provider):
        if not isinstance(provider, ConfigProvider):
           raise ValueError("expected a configuration provider")

        if id in self._providers:
            return

        self._providers[id] = provider

    def collect_check_configs(self):
        for source, provider in self._providers.iteritems():
            checksconfigs = provider.collect()
            for check, configs in checksconfigs:
                current_configs = self._check_configs.get(source).get(check, [])
                for config in configs:
                    if config in current_configs:
                        # skip existing ones in case we re-call this
                        continue
                    current_configs.append(config)

                self._check_configs[source][check] = current_configs

    def load_check_classes(self):
        for _, check_configs in self._check_configs:
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
        for source, check_configs in self._check_configs:
            for check_name, configs in check_configs.iteritems():
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

    def refresh_metadata(self):
        now = time.time()
        if (self._metadata['host_metadata']['last'] +
            self._metadata['host_metadata']['interval']) >= now:
            self._metadata['host_metadata']['meta']= get_metadata()
            self._metadata['host_metadata']['last']= now
            # set the updated metadata somewhere... Serializer?
