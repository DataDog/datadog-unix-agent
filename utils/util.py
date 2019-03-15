# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import logging

log = logging.getLogger(__name__)


def _is_affirmative(s):
    if s is None:
        return False
    # int or real bool
    if isinstance(s, int):
        return bool(s)
    # try string cast
    try:
        return s.lower() in ('yes', 'true', '1')
    except AttributeError:
        log.info("unexpected type for {} - defaulting to False".format(s))
        return False  # if we can't cast, just false
