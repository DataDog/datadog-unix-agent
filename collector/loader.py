# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import inspect
import logging

log = logging.getLogger(__name__)


class Loader(object):

    def load(self, name):
        '''Load Check class. Abstract.'''
        pass

    def _get_check_class(self, check_module):
        '''Return the corresponding check class for a check name if available.'''
        from datadog_checks.checks import AgentCheck

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
