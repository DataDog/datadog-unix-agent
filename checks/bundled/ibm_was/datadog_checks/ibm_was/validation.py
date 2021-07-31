# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
REQUIRED_QUERY_FIELDS = ['stat', 'metric_prefix']


def validate_query(query):
    for field in REQUIRED_QUERY_FIELDS:
        if field not in query:
            raise ValueError("Custom Query: {} missing required field: {}. Skipping".format(query, field))
