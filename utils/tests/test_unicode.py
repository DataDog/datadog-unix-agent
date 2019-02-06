# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import json
import pytest

from utils.unicode import ensure_unicode


def test_ensure_unicode(unicode_payload):
    # This test has been inherited from the python2 implementation
    # and doesn't make much sense anymore as all strings are unicode
    # on python3. Now we just check we can encode bytes to strings
    # with the `ensure_unicode` function - which is the closest we
    # can get to that previous scenario.

    # should raise
    with pytest.raises(TypeError):
        json.dumps(unicode_payload)

    payload = unicode_payload
    payload['series'] = ensure_unicode(payload['series'])
    try:
        json.dumps(unicode_payload)
    except UnicodeDecodeError:
        pytest.fail("Exception should not have been raised")
