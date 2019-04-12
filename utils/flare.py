# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import os
import zipfile
import logging
import datetime
import shutil
import urllib.parse
import tempfile

import requests

from .network import get_proxy, get_site_url
from .hostname import get_hostname
from .strip import Replacer
from .platform import get_os
from config import config

log = logging.getLogger(__name__)


class Flare(object):
    TIMEOUT = 60
    MAX_UPLOAD_SIZE = 10485000
    STATUS_FILE = 'status.log'
    DATADOG_SUPPORT_URL = '/support/flare'
    DEFAULT_REPLACERS = [
        Replacer(r'[a-fA-F0-9]{27}([a-fA-F0-9]{5})', r'***************************\1', None),  # api key
        Replacer(r'[a-fA-F0-9]{35}([a-fA-F0-9]{5})', r'***************************\1', None),  # application key
        Replacer(r'([A-Za-z]+\:\/\/|\b)([A-Za-z0-9_]+)\:([^\s-]+)\@', r'\1\2:********@', None),  # uris
        Replacer(Replacer.yaml_key_match_pattern(r'pass(word)?'), r'\1 ********', ['pass']),  # passwords
        Replacer(Replacer.yaml_key_match_pattern(r'token'), r'\1 ********', ['token']),  # tokens
    ]

    def __init__(self, paths=[], compression=zipfile.ZIP_DEFLATED, version=None, case_id=None, email=None):
        self._filename = "datadog-agent-{}.zip".format(datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"))
        self._tempdir = tempfile.mkdtemp(suffix='flare')
        self._compression = zipfile.ZIP_DEFLATED
        self._mode = 'w'
        self._paths = set(paths)
        self._replacers = list(self.DEFAULT_REPLACERS)

        # flare case
        self._hostname = get_hostname()
        self._case_id = int(case_id) if case_id else None
        self._email = email
        self._agent_version = version

    def redact(self, path):
        try:
            redacted = []
            with open(path, 'r') as fp:
                for line in fp.readlines():
                    for replacer in self._replacers:
                        line = replacer.replace(line)

                    redacted.append(line)
        except FileNotFoundError:
            log.error("unable to load file %s for redacting", path)
            raise

        return redacted

    def add_replacer(self, replacer):
        if replacer:
            self._replacers.append(replacer)

    def add_path(self, path):
        if not path or not os.path.exists(path):
            return
        if os.path.isdir(path):
            self._paths.add(path)
        else:
            self._paths.add(os.path.dirname(path))

    def get_archive_path(self):
        return os.path.join(self._tempdir, self._filename)

    def create_archive(self, status=None):
        flarepath = self.get_archive_path()
        with zipfile.ZipFile(flarepath, self._mode, self._compression) as flare_zip:
            for path in self._paths:
                try:
                    for root, dirs, files in os.walk(path):
                        for fp in files:
                            try:
                                redacted = self.redact(os.path.join(root, fp))
                                flare_zip.writestr(os.path.join(root, fp), ''.join(redacted))
                            except Exception:
                                log.error("unable to add file %s in path %s to flare", os.path.join(root, fp), path)
                except Exception as e:
                    log.error("unable to add path %s to zip archive: %s", path, e)

            if status:
                flare_zip.writestr(self.STATUS_FILE, status)

        return flarepath

    def _validate_size(self):
        return (os.path.getsize(self.get_archive_path()) <= self.MAX_UPLOAD_SIZE)

    def submit(self):
        endpoint = self.DATADOG_SUPPORT_URL
        if self._case_id:
            endpoint = urllib.parse.urljoin(endpoint, str(self._case_id))

        base_uri = get_site_url(config.get('dd_url'), site=config.get('site'))
        endpoint = urllib.parse.urljoin(endpoint, "?api_key={}".format(config.get('api_key')))
        url = urllib.parse.urljoin(base_uri, endpoint)

        flare_path = self.get_archive_path()
        if not os.path.exists(flare_path):
            return False, None

        if not self._validate_size():
            log.info("%s won't be uploaded, its size is too large.\n"
                        "You can send it directly to support by email.", flare_path)
            return False, None

        log.info("Uploading %s to Datadog Support", flare_path)
        with open(flare_path, 'rb') as flare_file:
            try:
                requests_options = {
                    'data': {
                        'case_id': self._case_id,
                        'hostname': self._hostname,
                        'email': self._email,
                        'agent_version': self._agent_version,
                        'platform': get_os(),
                    },
                    'files': {'flare_file': flare_file},
                    'timeout': self.TIMEOUT
                }

                proxies = get_proxy()
                if proxies:
                    requests_options['proxies'] = proxies

                resp = requests.post(url, **requests_options)
            except requests.exceptions.Timeout:
                log.error("Connection timout to: %s", url)
                return False, None

            success = False
            case_id = None
            if resp.status_code in (400, 404, 413):
                log.error("Error code %d received while uploading flare to %s: %s, dropping it",
                        resp.status_code, url, str(resp.text))
            elif resp.status_code == 403:
                log.error("API Key invalid, cannot submit flare")
            elif resp.status_code >= 400:
                log.error("error %d while sending flare to %s, try again later", resp.status_code, url)
            else:
                log.debug("Successfully posted payload to %s: %s", url, resp.text)
                success = True
                try:
                    case_id = resp.json().get('case_id', None)
                except ValueError as e:
                    log.info("bogus response after successful upload - could not retrieve case id: %s", e)

        return success, case_id

    def cleanup(self):
        if os.path.exists(self._tempdir):
            shutil.rmtree(self._tempdir)
