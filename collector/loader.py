# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import inspect
import logging

log = logging.getLogger(__name__)


class Loader(object):

    def load(self, name):
        return self._get_check_class(name)

    def _get_check_class(self, check_name):
        '''Return the corresponding check class for a check name if available.'''
        from datadog_checks.checks import AgentCheck
        check_class = None

        check_module, err = self._get_check_module(check_name)
        if err:
            return err

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

    def _get_check_module(self, check_name):
        '''Attempt to load the check module from places.'''
        pass
