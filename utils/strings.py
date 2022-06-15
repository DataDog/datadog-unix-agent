# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

def skip_blank_lines(f):
    for ln in f:
        line = ln.rstrip()
        if line:
            yield line
