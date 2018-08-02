# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

from .__about__ import __version__

__all__ = [
    '__version__'
]

__path__ = __import__('pkgutil').extend_path(__path__, __name__)
