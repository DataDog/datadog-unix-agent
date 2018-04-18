# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

def unicode_metrics(metrics):
    for i, metric in enumerate(metrics):
        for key, value in metric.items():
            if isinstance(value, basestring):
                metric[key] = unicode(value, errors='replace')
            elif isinstance(value, tuple) or isinstance(value, list):
                value_list = list(value)
                for j, value_element in enumerate(value_list):
                    if isinstance(value_element, basestring):
                        value_list[j] = unicode(value_element, errors='replace')
                metric[key] = tuple(value_list)
        metrics[i] = metric
    return metrics
