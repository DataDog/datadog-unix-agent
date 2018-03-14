# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

from importlib import import_module
import traceback
import logging

from .loader import Loader


log = logging.getLogger(__name__)

DD_WHEEL_NAMESPACE = "datadog_checks"


class WheelLoader(Loader):

    def __init__(self, *args, **kwargs):
        self.namespace = kwargs.get('namespace')
        super(WheelLoader, self).__init__(*args, **kwargs)

    def load(self, name):
        '''Load Check class.'''
        check_module, error = self._get_check_module(name)
        if check_module:
            check_class = self._get_check_class(check_module)
            return check_class, None
        else:
            return None, error

    def _get_check_module(self, check_name):
        '''Attempt to load the check module from places.'''

        try:
            module_name = "{}.{}".format(self.namespace, check_name)
            check_module = import_module(module_name)
        except Exception as e:
            traceback_message = traceback.format_exc()
            # Log at debug level since this code path is expected if the check is not installed as a wheel
            log.debug('Unable to import check module %s from site-packages: %s', check_name, e)
            return None, {'error': e, 'traceback': traceback_message}

        return check_module, None
