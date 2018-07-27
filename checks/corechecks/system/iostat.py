# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

from utils.process import get_subprocess_output
from checks import AgentCheck

class IOStat(AgentCheck):
    SCHEMA = {
        'Vadapter': {
            'sections': ['xfers', 'read', 'write', 'queue'],
            'xfers': {
                'cols': ['kbps', 'tps', 'blks.read', 'blks.write', 'partition_id'],
                'tags': ['partition_id'],
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
        }
    }
    TABLE_SEP = '--------------------'

    def check(self, instance):
        output, _, _ = get_subprocess_output(['iostat', '-Dsal', '1', '1'], self.log)
        stats = filter(None, output.splitlines())
        mode = ''
        for line in stats[4:]:
            if line.startswith(TABLE_SEP):
                continue

            for m in self.MODES:
                if line.startswith(m):
                    mode = m
                    expected_fields_no = 0
                    for section in self.SCHEMA[mode]['sections']:
                        expected_fields_no += len(SCHEMA[mode][section]['cols'])
                    expected_fields_no += 1  # the device
                    continue

            fields = line.split(' ')
            fields = filter(None, fields)
            if len(fields) != expected_fields_no:
                continue

            device = fields[0]

            metrics = {}
            tags = ["{mode}:{device}".format(mode=mode.lower(), device=device.lower())]
            section_idx = 1  # we start after the device
            for section in self.SCHEMA[mode]['section']:
                for idx, colname in enumerate(self.SCHEMA[mode][section]['cols']):
                    if colname not in self.SCHEMA[mode][section]['tags']:
                        metrics["{mode}.{name}".format(mode=mode.lower(), name=colname)] = float(fields[section_idx+idx])
                    else:
                        tags.append("{tag}:{val}".format(tag=colname, val=fields[section_idx+idx]))
                section_idx += len(self.SCHEMA[mode][secion]['cols'])

            for name, value in metrics.iteritems():
                self.gauge("system.iostat.{}".format(name), value, tags=tags)
