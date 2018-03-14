# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import os
import tempfile
import pytest

from config import Config

@pytest.fixture
def conf():
    return Config()

def test_init(conf):
    assert conf.search_paths == set()
    assert conf.conf_name == "datadog.yaml"
    assert conf.env_prefix == "DD_"
    assert conf.env_bindings == set()
    assert conf.data == {}
    assert conf.defaults == {}

def test_empty_conf(conf):
    assert conf.get("test") is None
    assert conf.load() is None

def test_default(conf):
    conf.set_default("test", 21)
    conf.load()
    assert conf.get("test") == 21

def test_set_and_reset(conf):
    assert conf.get("test") is None
    conf.set("test", 21)
    assert conf.get("test") == 21
    conf.reset("test")
    assert conf.get("test") is None

def test_load(conf):
    fd, tmpfile = tempfile.mkstemp(prefix="datadog-unix-agent_test_")
    os.write(fd, "---\ntest: 123\nlist: [1, 2, 3]")

    conf.add_search_path(os.path.dirname(tmpfile))
    conf.conf_name = os.path.basename(tmpfile)
    conf.load()

    assert conf.get("test") == 123
    assert conf.get("list") == [1, 2, 3]

    os.close(fd)
    os.remove(tmpfile)

def test_get(conf):
    fd, tmpfile = tempfile.mkstemp(prefix="datadog-unix-agent_test_")
    os.write(fd, "---\ntest: 123\ntest2: true\nlist: [1, 2, 3]")

    os.environ["DD_test2"] = "env_val"
    os.environ["DD_test3"] = "env_val2"

    conf.add_search_path(os.path.dirname(tmpfile))
    conf.conf_name = os.path.basename(tmpfile)

    conf.set_default("test1", "default")
    conf.set_default("test2", "default")
    conf.bind_env("test2")
    conf.bind_env_and_set_default("test3", False)
    conf.load()

    assert conf.get("test1") == "default"
    assert conf.get("test2") == "env_val"
    assert conf.get("test3") == "env_val2"
    assert conf.get("list") == [1, 2, 3]

    os.close(fd)
    os.remove(tmpfile)

def test_validate_aggregates_sane(conf):
    fd, tmpfile = tempfile.mkstemp(prefix="datadog-unix-agent_test_")
    os.write(fd, "---\ntest: 123\ntest2: true\nhistogram_aggregates: [min, max, median]")

    conf.add_search_path(os.path.dirname(tmpfile))
    conf.conf_name = os.path.basename(tmpfile)
    conf.load()

    assert isinstance(conf.get("histogram_aggregates"), list)
    assert len(conf.get("histogram_aggregates")) == 3
    for t in ['min', 'max', 'median']:
        assert t in conf.get("histogram_aggregates")

    os.close(fd)
    os.remove(tmpfile)

def test_validate_aggregates_sanitized(conf):
    fd, tmpfile = tempfile.mkstemp(prefix="datadog-unix-agent_test_")
    os.write(fd, "---\ntest: 123\ntest2: true\nhistogram_aggregates: [min, max, median, foo]")

    conf.add_search_path(os.path.dirname(tmpfile))
    conf.conf_name = os.path.basename(tmpfile)
    conf.load()

    assert isinstance(conf.get("histogram_aggregates"), list)
    assert len(conf.get("histogram_aggregates")) == 3
    for t in ['min', 'max', 'median']:
        assert t in conf.get("histogram_aggregates")

    os.close(fd)
    os.remove(tmpfile)

def test_validate_percentiles(conf):
    fd, tmpfile = tempfile.mkstemp(prefix="datadog-unix-agent_test_")
    os.write(fd, "---\ntest: 123\ntest2: true\nhistogram_percentiles: [0.98, 0.23, 0.1321]")

    conf.add_search_path(os.path.dirname(tmpfile))
    conf.conf_name = os.path.basename(tmpfile)

    conf.load()

    assert len(conf.get("histogram_percentiles")) == 3
    for v in [0.98, 0.23, 0.13]:
        assert v in conf.get("histogram_percentiles")

    os.close(fd)
    os.remove(tmpfile)

def test_validate_percentiles_badval(conf):
    fd, tmpfile = tempfile.mkstemp(prefix="datadog-unix-agent_test_")
    os.write(fd, "---\ntest: 123\ntest2: true\nhistogram_percentiles: [0.98, foo]")

    conf.add_search_path(os.path.dirname(tmpfile))
    conf.conf_name = os.path.basename(tmpfile)

    conf.load()

    assert len(conf.get("histogram_percentiles")) == 1
    assert conf.get("histogram_percentiles") == [0.98]

    os.close(fd)
    os.remove(tmpfile)

def test_validate_percentiles_bounds(conf):
    fd, tmpfile = tempfile.mkstemp(prefix="datadog-unix-agent_test_")
    os.write(fd, "---\ntest: 123\ntest2: true\nhistogram_percentiles: [1, 0]")

    conf.add_search_path(os.path.dirname(tmpfile))
    conf.conf_name = os.path.basename(tmpfile)

    conf.load()

    assert len(conf.get("histogram_percentiles")) == 0

    os.close(fd)
    os.remove(tmpfile)
