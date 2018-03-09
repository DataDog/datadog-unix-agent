from importlib import import_module
import traceback
import logging

from .loader import Loader

log = logging.getLogger(__name__)

DD_WHEEL_NAMESPACE = "datadog_checks"


class WheelsLoader(Loader):

    def _get_check_module(self, check_name):
        '''Attempt to load the check module from places.'''
        error = None
        traceback_message = None

        try:
            check_module = import_module("{}.{}".format(DD_WHEEL_NAMESPACE, check_name))
        except Exception as e:
            error = e
            traceback_message = traceback.format_exc()
            # Log at debug level since this code path is expected if the check is not installed as a wheel
            log.debug('Unable to import check module %s from site-packages: %s', check_name, e)

        if error:
            return None, {'error': error, 'traceback': traceback_message}

        return check_module, None
