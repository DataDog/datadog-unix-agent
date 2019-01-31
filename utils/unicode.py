# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

ENCODING = 'utf-8'

def ensure_unicode(data):
    for i, datum in enumerate(data):
        for key, value in list(datum.items()):
            if isinstance(value, bytes):
                datum[key] = value.decode(ENCODING, errors='replace')
            elif isinstance(value, tuple) or isinstance(value, list):
                value_list = list(value)
                for j, value_element in enumerate(value_list):
                    if isinstance(value_element, bytes):
                        value_list[j] = value_element.decode(ENCODING, errors='replace')
                datum[key] = tuple(value_list)
            elif isinstance(value, dict):
                datum[key] = ensure_unicode(value)
        data[i] = datum
    return data
