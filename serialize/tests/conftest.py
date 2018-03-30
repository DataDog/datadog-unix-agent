# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import os
import json

import pytest


HERE = os.path.dirname(os.path.realpath(__file__))
FIXTURE_PATH = os.path.join(HERE, 'fixtures')


@pytest.fixture(scope='session')
def legacy_payload():
    with open(FIXTURE_PATH + '/legacy_payload.json') as f:
        legacy_payload = json.load(f)

    return legacy_payload


@pytest.fixture(scope='session')
def service_check_payload():
    with open(FIXTURE_PATH + '/sc_payload.json') as f:
        service_check_payload = json.load(f)

    return service_check_payload
