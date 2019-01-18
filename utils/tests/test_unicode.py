# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import json
import pytest

from utils.unicode import unicode_metrics


def test_unicode_metrics(unicode_payload):
    # This test has been inherited from the python2 implementation
    # and doesn't make much sense anymore as all strings are unicode
    # on python3. Now we just check we can encode bytes to strings
    # with the `unicode_metrics` function - which is the closest we
    # can get to that previous scenario.

    # should raise
    with pytest.raises(TypeError):
        json.dumps(unicode_payload)

    payload = unicode_payload
    payload['series'] = unicode_metrics(payload['series'])
    try:
        json.dumps(unicode_payload)
    except UnicodeDecodeError:
        pytest.fail("Exception should not have been raised")
