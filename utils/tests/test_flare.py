# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import mock
import pytest

import os
import datetime
import tempfile
import shutil
import zipfile
import requests

from utils.flare import Flare

CONTENTS = {
    'marvel': 'Avengers: Ironman, Hulk, Spiderman, Thor, Captain American,...',
    'dc': 'Justice League: Superman, Batman, WonderWoman, Flash, Aquaman...',
}


@pytest.fixture
def requests_ok():
    resp = requests.Response()
    resp.status_code = 200
    return resp

@pytest.fixture
def requests_nok():
    resp = requests.Response()
    resp.status_code = 400
    return resp

@pytest.fixture(scope="module")
def zip_contents():
    zip_location = tempfile.mkdtemp(suffix='flare')
    for key, value in CONTENTS.iteritems():
        with open(os.path.join(zip_location, key), 'w') as fp:
            fp.write(value)

    yield zip_location  # provide the fixture value

    if os.path.exists(zip_location):
        shutil.rmtree(zip_location)


def test_flare_basic(zip_contents, requests_ok):
    my_flare = Flare(paths=[zip_contents])

    expected_flare_path = "datadog-agent-{}.zip".format(
        datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"))

    assert os.path.basename(my_flare.get_archive_path()) == expected_flare_path

    flare_path = my_flare.create_archive()
    assert os.path.exists(flare_path)
    assert zipfile.is_zipfile(flare_path)

    with zipfile.ZipFile(flare_path, 'r') as flare_zip:
        archive_contents = flare_zip.infolist()
        for content in archive_contents:
            assert os.path.basename(content.filename) in CONTENTS
            assert content.compress_type == zipfile.ZIP_DEFLATED

    with mock.patch('requests.post', return_value=requests_ok):
        assert my_flare.submit()

    my_flare.cleanup()
    assert not os.path.exists(flare_path)

def test_flare_400(zip_contents, requests_nok):
    my_flare = Flare(paths=[zip_contents])
    my_flare.create_archive()

    with mock.patch('requests.post', return_value=requests_nok):
        assert not my_flare.submit()

    my_flare.cleanup()
    assert not os.path.exists(my_flare.get_archive_path())

def test_flare_proxy_timeout(zip_contents):
    my_flare = Flare(paths=[zip_contents])
    my_flare.create_archive()

    with mock.patch('requests.post') as requests_mock:
        requests_mock.side_effect = requests.exceptions.Timeout('fake proxy timeout')
        assert not my_flare.submit()

    my_flare.cleanup()
    assert not os.path.exists(my_flare.get_archive_path())

def test_flare_too_large(zip_contents):
    my_flare = Flare(paths=[zip_contents])
    my_flare.MAX_UPLOAD_SIZE = 1
    my_flare.create_archive()

    assert not my_flare._validate_size()
    with mock.patch('requests.post', return_value=requests_ok):
        assert not my_flare.submit()

    my_flare.cleanup()
    assert not os.path.exists(my_flare.get_archive_path())
