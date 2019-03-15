# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

from utils.util import _is_affirmative


def test_is_affirmative():
    assert not _is_affirmative(None)
    assert not _is_affirmative(0)
    assert not _is_affirmative('0')
    assert not _is_affirmative('False')
    assert not _is_affirmative('foo')
    assert not _is_affirmative(False)
    assert not _is_affirmative(object())
    assert _is_affirmative(1)
    assert _is_affirmative('1')
    assert _is_affirmative('Yes')
    assert _is_affirmative('yes')
    assert _is_affirmative('True')
    assert _is_affirmative('true')
    assert _is_affirmative(True)
