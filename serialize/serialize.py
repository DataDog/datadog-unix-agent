# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import json


class Serializer(object):
    JSON_HEADERS = {'Content-Type': 'application/json'}

    def __init__(self, aggregator, forwarder):
        self._aggregator = aggregator
        self._forwarder = forwarder

    @classmethod
    def split_payload(cls, payload):
        # NOTE: don't think we're going to need this

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

    def serialize(self, add_meta):
        metrics = {'series': self._aggregator.flush()}
        service_checks = self._aggregator.flush_service_checks()
        events = self._aggregator.flush_events()

        return (json.dumps(metrics),
                json.dumps(service_checks),
                json.dumps(events))

    def serialize_and_push(self, add_meta=False):
        metrics, service_checks, events = self.serialize(add_meta)

        extra_headers = self.JSON_HEADERS
        if metrics:
            self._forwarder.submit_v1_series(
                metrics, extra_headers)
        if service_checks:
            self._forwarder.submit_v1_service_checks(
                service_checks, extra_headers)
        if events:
            self._forwarder.submit_v1_intake(
                events, extra_headers)

    def submit_metadata(self, metadata):
        extra_headers = self.JSON_HEADERS
        self._forwarder.submit_v1_intake(metadata, extra_headers)
