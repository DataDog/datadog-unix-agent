# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.


def freeze(o):
    """
    Freezes any mutable object including dictionaries and lists for hashing.
    Accepts nested dictionaries.
    """
    if isinstance(o, dict):
        return frozenset(dict([(k, freeze(v)) for k, v in o.iteritems()]).iteritems())

    if isinstance(o, list):
        return tuple([freeze(v) for v in o])

    if isinstance(o, tuple):
        return tuple([freeze(v) for v in o])

    return o


def hash_mutable(m):
    return hash(freeze(m))
