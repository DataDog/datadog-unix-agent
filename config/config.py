import os
import yaml
import logging


log = logging.getLogger(__name__)

class Config(object):

    DEFAULT_CONF_NAME = "datadog.yaml"
    DEFAULT_ENV_PREFIX = "DD_"

    def __init__(self, conf_name=DEFAULT_CONF_NAME, env_prefix=DEFAULT_ENV_PREFIX):
        self.search_paths = set()
        self.conf_name = conf_name
        self.env_prefix = env_prefix
        self.env_bindings = set()
        self.data = {}
        self.defaults = {}

    def add_search_path(self, search_path):
        self.search_paths.add(search_path)

    def load(self):
        if self.search_paths:
            for path in self.search_paths:
                conf_path = os.path.join(path, self.conf_name)
                if os.path.isfile(conf_path):
                    with open(conf_path, "r") as f:
                        self.data = yaml.load(f)
                    break
            else:
                log.error("Could not find %s in search_paths: %s", self.conf_name, self.search_paths)

        for env_var in self.env_bindings:
            key = self.env_prefix + env_var
            if key in os.environ:
                self.data[env_var] = os.environ[key]

    def set_default(self, key, value):
        self.defaults[key] = value

    def set(self, key, value):
        self.data[key] = value

    def reset(self, key):
        del self.data[key]

    def bind_env(self, key):
        self.env_bindings.add(key)

    def bind_env_and_set_default(self, key, value):
        self.bind_env(key)
        self.set_default(key, value)

    def get(self, key, default=None):
        return self.data.get(key, self.defaults.get(key, default))
