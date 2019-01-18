# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

from .config import Config
from config import default


config = Config()
default.init(config)

__all__ = ['Config', 'config', 'default']
