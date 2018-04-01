# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import json


class Serializer(object):

    def __init__(self, aggregator, forwarder):
        self._aggregator = aggregator
        self._forwarder = forwarder
        self._metadata = None

    @classmethod
    def split_payload(cls, payload):

        metrics_payload = {"series": []}

        # See https://github.com/DataDog/dd-agent/blob/5.11.1/checks/__init__.py#L905-L926 for format
        for ts in payload['metrics']:
            sample = {
                "metric": ts[0],
                "points": [(ts[1], ts[2])],
                "source_type_name": "System",
            }

            if len(ts) >= 4:
                # Default to the metric hostname if present
                if ts[3].get('hostname'):
                    sample['host'] = ts[3]['hostname']
                else:
                    # If not use the general payload one
                    sample['host'] = payload['internalHostname']

                if ts[3].get('type'):
                    sample['type'] = ts[3]['type']
                if ts[3].get('tags'):
                    sample['tags'] = ts[3]['tags']
                if ts[3].get('device_name'):
                    sample['device'] = ts[3]['device_name']

            metrics_payload["series"].append(sample)

        del payload['metrics']

        service_checks_payload = payload["service_checks"]

        del payload["service_checks"]

        return payload, metrics_payload, service_checks_payload

    def set_metadata(self, metadata):
        self._metadata = metadata

    def serialize(self, add_meta=False):

        metrics = self._aggregator.flush()
        payload, metrics_payload, service_checks_payload = self.split_payload({'metrics': metrics})

        # TODO: do this right
        if add_meta:
            payload['meta'] = self._metadata

        extra_headers = {'Content-Type': 'application/json'}
        if metrics_payload:
            self._forwarder.submit_v1_series(
                json.dumps(metrics_payload), extra_headers)
        if service_checks_payload:
            self._forwarder.submit_v1_service_checks(
                json.dumps(service_checks_payload), extra_headers)
        if payload:
            self._forwarder.submit_v1_intake(
                json.dumps(payload), extra_headers)
