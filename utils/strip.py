# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import re


class Replacer(object):
    YAML_KEY_RE = r"(\s*(\w|_)*{key}(\w|_)*\s*:).+"

    def __init__(self, pattern, repl, hints=[]):
        self._re = re.compile(pattern)
        self._repl = repl
        self._hints = hints

    @classmethod
    def yaml_key_match_pattern(cls, key):
        return cls.YAML_KEY_RE.format(key=key)

    def replace(self, target):
        if not self._hints:
            return self._re.sub(self._repl, target)

        for hint in self._hints:
            if hint in target:
                return self._re.sub(self._repl, target)

        return target
