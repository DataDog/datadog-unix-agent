# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import inspect
import logging

log = logging.getLogger(__name__)


class Loader(object):

    def __init__(self, *args, **kwargs):
        super(Loader, self).__init__()

    def load(self, name):
        '''Load Check class. Abstract.'''
        raise NotImplementedError

    def _get_check_class(self, check_module):
        '''Return the corresponding check class for a check name if available.'''
        from checks import AgentCheck

        # We make sure that there is an AgentCheck class defined
        check_class = None
        classes = inspect.getmembers(check_module, inspect.isclass)
        for _, clsmember in classes:
            if clsmember == AgentCheck:
                continue
            if issubclass(clsmember, AgentCheck):
                check_class = clsmember
                if AgentCheck in clsmember.__bases__:
                    continue
                else:
                    break
        return check_class
