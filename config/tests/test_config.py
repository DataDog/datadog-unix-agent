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
