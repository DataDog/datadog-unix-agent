import imp
import traceback
import logging

from .loader import Loader


log = logging.getLogger(__name__)

class CheckLoader(Loader):

    def __init__(self):
        self._places = []

    def add_place(self, place):
        self._places.append(place)

    def _get_check_module(self, check_name):
        '''Attempt to load the check module from places.'''
        errors = {}
        location = None

        for place in self._places:
            error = None
            traceback_message = None
            location = place
            try:
                check_module = imp.load_source('checksd_%s' % check_name, place)
            except Exception as e:
                error = e
                traceback_message = traceback.format_exc()
                # There is a configuration file for that check but the module can't be imported
                log.exception('Unable to import check module %s.py from location %s' % check_name)

            if not error:
                break

            errors[place] = {'error': error, 'traceback': traceback_message}

        if check_module:
            return check_module, location, None

        return None, None, errors
