# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import os
import imp
import traceback
import logging

from .loader import Loader


log = logging.getLogger(__name__)


class CheckLoader(Loader):

    def __init__(self, *args, **kwargs):
        self._places = []
        super(CheckLoader, self).__init__(*args, **kwargs)

    def add_place(self, place):
        self._places.append(place)

    def load(self, name):
        '''Load Check class.'''
        errors = {}
        for place in self._places:
            check_module, error = self._get_check_module(name, place)

            check_class = self._get_check_class(check_module)
            if check_class:
                return check_class, None
            else:
                errors[place] = error

        return None, errors

    def _get_check_module(self, check_name, place):
        '''Attempt to load the check module from places.'''

        try:
            source = os.path.join(place, "{}.py".format(check_name))
            check_module = imp.load_source('checksd_%s' % check_name, source)
        except Exception as e:
            traceback_message = traceback.format_exc()
            # There is a configuration file for that check but the module can't be imported
            log.debug('Unable to import check module %s.py from location %s' % (check_name, place))
            return None, {'error': e, 'traceback': traceback_message}

        return check_module, None
