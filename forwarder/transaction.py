# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import time
import logging
import re
import traceback
import requests

from utils.http import get_shared_requests

log = logging.getLogger(__name__)


class Transaction(object):
    API_KEY_REPLACEMENT = re.compile(r"api_key=*\w+(\w{5})")
    RETRY_INTERVAL = 5   # 5 seconds
    MAX_RETRY_INTERVAL = 90  # wait up to 90 s between retries

    def __init__(self, payload, domain, endpoint, options=None):
        """
        payload: serialized data to send
        domain:  base URL (e.g. https://unix.agent.datadoghq.com)
        endpoint: path portion (/intake/, /api/v1/series, etc.)
        options: dict of requests options (headers, proxies, timeout, verify)
        """
        self.payload = payload
        self.domain = domain
        self.endpoint = endpoint
        self.options = options or {}
        self.created_at = time.time()
        self.nb_try = 0
        self.next_flush = None

    # --------------------------------------------------------------------------
    # Helpers
    # --------------------------------------------------------------------------
    def get_endpoint(self):
        """Mask api_key query parameter for logs."""
        return self.API_KEY_REPLACEMENT.sub("api_key=***************************\\1", self.endpoint)

    # --------------------------------------------------------------------------
    # Processing
    # --------------------------------------------------------------------------
    def process(self):
        """Attempt to POST the payload once. Returns True on success."""
        self.nb_try += 1

        url = self.domain + self.endpoint
        log_url = self.domain + self.get_endpoint()
        shared_requests = get_shared_requests()

        # merge default options
        request_opts = self.options.copy()
        timeout = request_opts.get("timeout", 10)
        headers = request_opts.get("headers", {})
        proxies = request_opts.get("proxies")
        verify = request_opts.get("verify", True)

        try:
            resp = shared_requests.post(
                url,
                data=self.payload,
                timeout=timeout,
                headers=headers,
                proxies=proxies,
                verify=verify,
            )
        except requests.exceptions.Timeout as e:
            log.error("Connection timeout to: %s\n%s",
                      log_url, e)
            return False
        except requests.exceptions.ProxyError as e:
            log.error("Unable to connect to %s through proxy: %s\n%s",
                      log_url, proxies, e)
            return False
        except requests.exceptions.SSLError as e:
            log.error("SSL verification failed for %s: %s",
                      log_url, e)
            return False
        except requests.exceptions.ConnectionError as e:
            log.error("Unable to submit payload to %s, possible network issue: %s",
                      log_url, e)
            return False
        except Exception as e:
            log.error("Unexpected error submitting to %s: %s",
                      log_url, e)
            return False

        # ------------------------------------------------------------------
        # Response handling (same semantics as before)
        # ------------------------------------------------------------------
        if resp.status_code in (400, 404, 413):
            log.error(
                "Error code %d received while sending transaction to %s: %s, dropping it",
                resp.status_code, log_url, resp.text,
            )
            log.debug("Failed payload: %s", self.payload)
        elif resp.status_code == 403:
            log.error("API Key invalid, dropping transaction for %s", log_url)
        elif resp.status_code >= 400:
            log.error(
                "Error %d while sending transaction to %s, rescheduling it",
                resp.status_code, log_url,
            )
            return False
        else:
            log.info("Successfully posted payload to %s: (%s) %s",
                     log_url, resp.status_code, resp.text)

        return True

    # --------------------------------------------------------------------------
    # Retry / scheduling
    # --------------------------------------------------------------------------
    def reschedule(self):
        interval = min(self.nb_try * self.RETRY_INTERVAL,
                       self.MAX_RETRY_INTERVAL)
        self.next_flush = time.time() + interval
