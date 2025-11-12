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

CASE_NO = 12345


@pytest.fixture
def requests_ok():
    resp = requests.Response()
    resp._content = "{{\"case_id\": {}}}".format(CASE_NO).encode()
    resp.status_code = 200
    return resp


@pytest.fixture
def requests_ok_no_case():
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
    for key, value in CONTENTS.items():
        with open(os.path.join(zip_location, key), 'w') as fp:
            fp.write(value)

    yield zip_location  # provide the fixture value

    if os.path.exists(zip_location):
        shutil.rmtree(zip_location)


def test_flare_basic(zip_contents, requests_ok, requests_ok_no_case):
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

    # --- First test: request returns case_id ---
    with mock.patch('utils.flare.get_shared_requests') as mock_get_session:
        mock_session = mock.Mock()
        mock_session.post.return_value = requests_ok
        mock_get_session.return_value = mock_session

        success, case = my_flare.submit()
        assert success
        assert case == CASE_NO

    # --- Second test: request returns no case_id ---
    with mock.patch('utils.flare.get_shared_requests') as mock_get_session:
        mock_session = mock.Mock()
        mock_session.post.return_value = requests_ok_no_case
        mock_get_session.return_value = mock_session

        success, case = my_flare.submit()
        assert success
        assert case is None

    my_flare.cleanup()
    assert not os.path.exists(flare_path)


def test_flare_400(zip_contents, requests_nok):
    my_flare = Flare(paths=[zip_contents])
    my_flare.create_archive()

    with mock.patch('utils.flare.get_shared_requests') as mock_get_session:
        mock_session = mock.Mock()
        mock_session.post.return_value = requests_nok
        mock_get_session.return_value = mock_session

        success, case = my_flare.submit()
        assert not success
        assert case is None

    my_flare.cleanup()
    assert not os.path.exists(my_flare.get_archive_path())


def test_flare_proxy_timeout(zip_contents):
    my_flare = Flare(paths=[zip_contents])
    my_flare.create_archive()

    with mock.patch('utils.flare.get_shared_requests') as mock_get_session:
        mock_session = mock.Mock()
        mock_session.post.side_effect = requests.exceptions.Timeout(
            "fake proxy timeout")
        mock_get_session.return_value = mock_session

        success, case = my_flare.submit()
        assert not success
        assert case is None

    my_flare.cleanup()
    assert not os.path.exists(my_flare.get_archive_path())


def test_flare_too_large(zip_contents):
    my_flare = Flare(paths=[zip_contents])
    my_flare.MAX_UPLOAD_SIZE = 1
    my_flare.create_archive()

    assert not my_flare._validate_size()
    with mock.patch('utils.flare.get_shared_requests') as mock_get_session:
        mock_session = mock.Mock()
        mock_session.post.return_value = requests_ok
        mock_get_session.return_value = mock_session

        success, case = my_flare.submit()
        assert not success
        assert case is None

    my_flare.cleanup()
    assert not os.path.exists(my_flare.get_archive_path())


def test_flare_endpoint_with_case_id(zip_contents):
    """When case_id is set, the endpoint should include it."""
    my_flare = Flare(paths=[zip_contents])
    my_flare._case_id = 1234
    my_flare.create_archive()

    # Mock the session returned by get_shared_requests()
    with mock.patch('utils.flare.get_shared_requests') as mock_get_session:
        mock_session = mock.Mock()
        mock_resp = requests.Response()
        mock_resp.status_code = 200
        mock_resp._content = b'{"case_id": 1234}'

        mock_session.post.return_value = mock_resp
        mock_get_session.return_value = mock_session

        success, case = my_flare.submit()
        assert success
        assert case == 1234

        # Grab the actual URL used in the call
        called_url = mock_session.post.call_args[0][0]
        assert called_url.endswith(
            '/support/flare/1234'), f"unexpected endpoint: {called_url}"

    my_flare.cleanup()
    assert not os.path.exists(my_flare.get_archive_path())


def test_flare_includes_dd_api_key_header(zip_contents):
    """Ensure the DD-API-KEY header is included in the upload request when no case_id is set."""
    my_flare = Flare(paths=[zip_contents])
    my_flare.create_archive()  # no case_id set

    # Patch config.get so api_key returns a known value
    with mock.patch('utils.flare.config.get', side_effect=lambda key, **kwargs: 'test-api-key' if key == 'api_key' else None):
        with mock.patch('utils.flare.get_shared_requests') as mock_get_session:
            mock_session = mock.Mock()
            mock_resp = requests.Response()
            mock_resp.status_code = 200

            mock_session.post.return_value = mock_resp
            mock_get_session.return_value = mock_session

            success, case = my_flare.submit()
            assert success

            _, kwargs = mock_session.post.call_args
            headers = kwargs.get('headers', {})

            # Validate that DD-API-KEY header exists and has correct value
            assert 'DD-API-KEY' in headers, f"Missing DD-API-KEY header: {headers}"
            assert headers[
                'DD-API-KEY'] == 'test-api-key', f"Incorrect DD-API-KEY value: {headers}"

    my_flare.cleanup()
    assert not os.path.exists(my_flare.get_archive_path())
