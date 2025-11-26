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


# ---------------------------------------------------------------------------
# API key masking helpers
# ---------------------------------------------------------------------------

MIN_MASK_LEN = 27  # fixed minimum masking block

def mask_api_key_value(api_key):
    """
    Mask an API key with these rules:
      - ALWAYS prepend at least 27 '*' characters (fixed mask length).
      - If len >= 6: expose last 5 characters.
      - If len <= 5: expose last 1 character.
      - If len == 1: still mask as '*' * 27 + last character.
    """
    if not isinstance(api_key, str):
        return api_key

    length = len(api_key)

    # Special case: empty string remains unchanged
    if length == 0:
        return api_key

    # last 5 chars for real keys, last 1 for short keys
    if length >= 6:
        tail = api_key[-5:]
    else:
        tail = api_key[-1:]  # last char even if length == 1

    return '*' * MIN_MASK_LEN + tail
