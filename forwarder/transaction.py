# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import time
import requests
import logging
import re


from config import config

log = logging.getLogger(__name__)


class Transaction(object):
    API_KEY_REPLACEMENT = re.compile("api_key=*\\w+(\\w{5})")
    RETRY_INTERVAL = 5  # 5 second interval
    MAX_RETRY_INTERVAL = 90  # wait for a maximum of 90s to retry a transaction

    def __init__(self, payload, domain, endpoint, headers, proxies={}):
        self.payload = payload
        self.domain = domain
        self.endpoint = endpoint
        self.headers = headers
        self.created_at = time.time()
        self.nb_try = 0
        self.next_flush = None
        self.timeout = config.get("forwarder_timeout")
        self.proxies = proxies

    def get_endpoint(self):
        return self.API_KEY_REPLACEMENT.sub("api_key=***************************\\1", self.endpoint)

    def process(self):
        self.nb_try += 1

        url = self.domain + self.endpoint
        log_url = self.domain + self.get_endpoint()
        try:
            resp = requests.post(url, self.payload, headers=self.headers, timeout=self.timeout, proxies=self.proxies)
        except requests.exceptions.Timeout:
            log.error("Connection timout to: %s", log_url)
            return False
        except requests.exceptions.ProxyError:
            log.error("unable to connect through proxy: %s", log_url)
            return False

        if resp.status_code in (400, 404, 413):
            log.error("Error code %d received while sending transaction to %s: %s, dropping it",
                      resp.status_code, log_url, str(resp.text))
            log.debug("Failed payload: %s", self.payload)
        elif resp.status_code == 403:
            log.error("API Key invalid, dropping transaction for %s", log_url)
        elif resp.status_code >= 400:
            log.error("error %q while sending transaction to %q, rescheduling it", resp.status_code, log_url)
            return False
        else:
            log.debug("Successfully posted payload to %s: %s", log_url, resp.text)
        return True

    def reschedule(self):
        interval = min(self.nb_try * self.RETRY_INTERVAL, self.MAX_RETRY_INTERVAL)
        self.next_flush = time.time() + interval
