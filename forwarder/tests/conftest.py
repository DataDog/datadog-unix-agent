# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import pytest
import requests_mock


@pytest.fixture()
def m():
    with requests_mock.Mocker() as m:
        yield m

