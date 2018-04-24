# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import pytest

from utils.hash import (
    freeze,
    hash_mutable,
)


def test_freeze():
    sample_one = {'foo': 'bar'}
    sample_two = {'haz': 'qux'}

    freeze_one = freeze(sample_one)
    freeze_two = freeze(sample_two)

    try:
        hash(freeze_one)
        hash(freeze_two)
    except TypeError:
        pytest.fail('freeze() did not return immutable type')


def test_freeze_tuple_mutables():
    sample_one = {'foo': 'bar'}
    sample_two = {'haz': 'qux'}

    mutable_tuple = (sample_one, sample_two)
    try:
        hash(freeze(mutable_tuple))
    except TypeError:
        pytest.fail('freeze() did not return immutable type')


def test_hash_mutable():
    complex_dict = {
        'init_config': {},
        'instances': [
            {
                'name': 'foo',
                'url': 'localhost:5000',
                'tags': ['some', 'tags', 'here'],
            },
            {
                'name': 'foo2',
                'url': 'localhost:9000',
                'tags': ['different', 'tags', 'here'],
            },
        ]
    }

    try:
        hash_mutable(complex_dict)
    except TypeError:
        pytest.fail('hash_mutable() did not hash immutable type')
