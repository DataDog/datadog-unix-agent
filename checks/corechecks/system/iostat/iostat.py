# checks/corechecks/system/iostat/iostat.py
# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import math

from utils.process import get_subprocess_output
from checks import AgentCheck


class IOStatCheck(AgentCheck):
    """
    Core IOStat check for AIX. Parses iostat -Dsal output using static schema.
    """

    __slots__ = tuple()

    SCHEMA = {
        'Physical': {
            'sections': ['physical'],
            'physical': {
                'cols': ['kbps', 'tps', 'kb.read', 'kb.write'],
            },
        },
        'Adapter': {
            'sections': ['xfers'],
            'xfers': {
                'cols': ['kbps', 'tps', 'blks.read', 'blks.write'],
            },
        },
        'Vadapter': {
            'sections': ['xfers', 'read', 'write', 'queue'],
            'xfers': {
                'cols': ['kbps', 'tps', 'blks.read', 'blks.write', 'partition_id'],
                'tags': ['partition_id'],
            },
            'read': {
                'cols': ['rps', 'serv.avg', 'serv.min', 'serv.max'],
            },
            'write': {
                'cols': ['wps', 'serv.avg', 'serv.min', 'serv.max'],
            },
            'queue': {
                'cols': ['time.avg', 'time.min', 'time.max', 'wqsz.avg', 'sqsz.avg', 'serv.qfull'],
            },
        },
        'Disks': {
            'sections': ['xfers', 'read', 'write', 'queue'],
            'xfers': {
                'cols': ['tm.act.pct', 'bps', 'tps', 'blks.read', 'blks.write'],
            },
            'read': {
                'cols': ['rps', 'serv.avg', 'serv.min', 'serv.max', 'timeouts', 'fail'],
            },
            'write': {
                'cols': ['wps', 'serv.avg', 'serv.min', 'serv.max', 'timeouts', 'fail'],
            },
            'queue': {
                'cols': ['time.avg', 'time.min', 'time.max', 'wqsz.avg', 'sqsz.avg', 'serv.qfull'],
            },
        },
    }

    TABLE_SEP = '--------------------'

    def check(self, instance):
        output, _, _ = get_subprocess_output(['iostat', '-Dsal', '1', '1'], self.log)
        stats = [_f for _f in output.splitlines() if _f]
        mode = ''

        for line in stats[4:]:  # skip header lines
            if line.startswith(self.TABLE_SEP):
                continue

            # Detect mode (Physical, Adapter, Vadapter, Disks)
            for m in self.SCHEMA:
                if line.startswith(m):
                    mode = m
                    expected_fields = 1  # device column
                    for section in self.SCHEMA[m]['sections']:
                        expected_fields += len(self.SCHEMA[m][section]['cols'])
                    continue

            fields = [f for f in line.split(' ') if f]
            if len(fields) != expected_fields:
                continue

            tags = []
            metrics = {}

            # Physical is odd one out and does not include device name before fields
            if mode.lower() != 'physical':
                device = fields[0]
                tags = ["{mode}:{device}".format(mode=mode.lower(), device=device.lower())]

            section_idx = 1  # we start after the device
            for section in self.SCHEMA[mode]['sections']:
                for idx, colname in enumerate(self.SCHEMA[mode][section]['cols']):
                    try:
                        section_tag_cols = self.SCHEMA[mode][section].get('tags', [])
                        if colname in section_tag_cols:
                            tags.append("{tag}:{val}".format(tag=colname, val=fields[section_idx+idx]))
                        else:
                            metrics["{mode}.{section}.{name}".format(mode=mode.lower(), section=section, name=colname)] = \
                                self.extract_with_unit(fields[section_idx+idx])
                    except ValueError as e:
                        self.log.debug("unexpected value parsing metric %s", e)

                section_idx += len(self.SCHEMA[mode][section]['cols'])

            for name, value in metrics.items():
                self.gauge("system.iostat.{}".format(name), value, tags=tags)

    @classmethod
    def extract_with_unit(cls, value):
        unit_map = {
            'K': 1000,
            'M': 1000000,
            'G': 1000000000,
            'T': 1000000000000,
        }

        converted = None
        try:
            converted = float(value)
        except ValueError:
            for unit, factor in unit_map.items():
                if value.endswith(unit):
                    return float(value[:-1]) * factor
            raise

        if math.isnan(converted):
            raise ValueError("NaN is not an acceptable value")

        return converted
