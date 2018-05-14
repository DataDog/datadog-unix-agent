# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import json

from serialize import Serializer


def test_split(legacy_payload, service_check_payload):
    payload, metrics_payload, sc_payload = Serializer.split_payload(dict(legacy_payload))

    assert 'series' in metrics_payload
    for s in metrics_payload['series']:

        series = metrics_payload['series']
        payload['metrics'] = []

        for s in series:
            attributes = {}

            if s.get('type'):
                attributes['type'] = s['type']
            if s.get('host'):
                attributes['hostname'] = s['host']
            if s.get('tags'):
                attributes['tags'] = s['tags']
            if s.get('device'):
                attributes['device_name'] = s['device']

            formatted_sample = [
                s['metric'],
                s['points'][0][0],
                s['points'][0][1],
                attributes
            ]
            payload['metrics'].append(formatted_sample)

    del legacy_payload['service_checks']
    assert payload == legacy_payload
    assert sc_payload == service_check_payload


def test_serialize(mock_aggregator, mock_forwarder):
    serializer = Serializer(mock_aggregator, mock_forwarder)

    metrics_szd, metrics_count = serializer.serialize_metrics(False)
    assert metrics_szd
    service_checks_szd, service_checks_count = serializer.serialize_service_checks(False)
    assert service_checks_szd
    events_szd, events_count = serializer.serialize_events(False)
    assert events_szd

    metrics = json.loads(metrics_szd)
    service_checks = json.loads(service_checks_szd)
    events = json.loads(events_szd)

    assert metrics == mock_aggregator.series
    assert service_checks == mock_aggregator.service_checks
    assert events['events']['api'] == mock_aggregator.events


def test_serialize_and_push(mock_aggregator, mock_forwarder):
    aggregator = mock_aggregator
    forwarder = mock_forwarder
    serializer = Serializer(aggregator, forwarder)

    serializer.serialize_and_push(False)

    # assert fowarder correctly called
    forwarder.submit_v1_series.assert_called()
    forwarder.submit_v1_service_checks.assert_called()
    forwarder.submit_v1_intake.assert_called()
