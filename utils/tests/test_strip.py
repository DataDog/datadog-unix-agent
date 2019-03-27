# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import pytest

from utils.strip import Replacer


def test_strip_basic():
    key = "b31d41038b94e10f8131ae731c5712345"
    sensitive = "api_key: {key}".format(key=key)
    redacter = Replacer(r'[a-fA-F0-9]{27}([a-fA-F0-9]{5})', r'***************************\1', None)
    redacted_key = redacter.replace(key)
    redacted_yaml = redacter.replace(sensitive)
    assert key not in redacted_yaml
    assert redacted_yaml[-5:] == key[-5:]
    assert redacted_key in redacted_yaml
    assert redacted_key[0:-6] == '*'*27

def test_strip_hints():
    key = "b31d41038b94e10f8131ae731c5712345"
    sensitive = "api_key: {key}".format(key=key)
    redacter = Replacer(r'[a-fA-F0-9]{27}([a-fA-F0-9]{5})', r'***************************\1', ['api_key'])
    unredacted_key = redacter.replace(key)  # no hint match
    redacted_yaml = redacter.replace(sensitive)  # hint match

    assert unredacted_key == key
    assert key not in redacted_yaml
    assert redacted_yaml[-5:] == key[-5:]
    assert redacted_yaml == "api_key: {redacted}{unredacted}".format(redacted='*'*27, unredacted=key[-6:])

def test_key_matcher():
    passwd = "foobar"
    yaml_key = "pass(word)?"
    pattern = Replacer.yaml_key_match_pattern(yaml_key)

    sensitive = "    - password: {}  ".format(passwd)
    redacter = Replacer(pattern, r'\1 ********', ['pass'])
    redacted_yaml = redacter.replace(sensitive)

    assert passwd not in redacted_yaml
    assert redacted_yaml.endswith('password: ********')
