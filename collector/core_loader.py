# collector/core_loader.py

# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).

import importlib
import logging
import os

from .loader import Loader

log = logging.getLogger(__name__)


class CoreCheckLoader(Loader):
    """
    Loader that discovers corechecks under:

        checks.corechecks.<category>.<check_name>

    The loader is compatible with:
      * namespace packages (__path__ = _NamespacePath)
      * multi-root namespace paths
      * tests that create fake modules without __path__
      * folder/module layouts where the module filename differs from folder name
    """

    CORECHECK_ROOT = "checks.corechecks"

    def load(self, check_name):
        """
        Try to locate and import the corecheck module.

        Returns:
            (check_class, None) on success
            (None, None) if no matching corecheck is found
            (None, error_dict) if the module exists but import fails
        """
        log.debug("CoreCheckLoader: loading %s", check_name)

        # Import the root namespace (checks.corechecks)
        try:
            root_pkg = importlib.import_module(self.CORECHECK_ROOT)
        except Exception as e:
            log.debug("CoreCheckLoader: cannot import root package %s (%s)",
                      self.CORECHECK_ROOT, e)
            return None, None

        # Some test scaffolding creates simple modules without __path__
        if not hasattr(root_pkg, "__path__"):
            return None, None

        # Traverse namespace filesystem roots
        for root_path in root_pkg.__path__:
            if not os.path.isdir(root_path):
                continue

            # Enumerate category directories (e.g., system, net, ...)
            try:
                categories = os.listdir(root_path)
            except Exception:
                continue

            for category in categories:
                category_path = os.path.join(root_path, category)
                if not os.path.isdir(category_path):
                    continue

                # Each check resides under a folder named after the check
                check_path = os.path.join(category_path, check_name)
                if not os.path.isdir(check_path):
                    continue

                # Base import path for the check package
                #   checks.corechecks.<category>.<check_name>
                module_base = f"{self.CORECHECK_ROOT}.{category}.{check_name}"

                # Import the check package (__init__.py)
                try:
                    importlib.import_module(module_base)
                except Exception as e:
                    return None, {
                        'error': e,
                        'traceback': Loader._format_exception(e),
                    }

                # Identify the implementation .py module inside the directory.
                #
                # Exclude:
                #   __init__.py  - package initializer
                #   __about__.py - version metadata, not a check
                #
                py_files = [
                    f for f in os.listdir(check_path)
                    if f.endswith(".py") and f not in ("__init__.py", "__about__.py")
                ]
                if not py_files:
                    continue

                # Select the first .py file. A check dir should contain exactly one.
                module_name = os.path.splitext(py_files[0])[0]
                module_full = f"{module_base}.{module_name}"

                # Import the actual module containing the check class
                try:
                    mod = importlib.import_module(module_full)
                except Exception as e:
                    return None, {
                        'error': e,
                        'traceback': Loader._format_exception(e),
                    }

                # Extract the AgentCheck subclass from the module
                check_class = self._get_check_class(mod)
                if check_class:
                    log.debug("CoreCheckLoader: loaded corecheck '%s' from %s",
                              check_name, module_full)
                    return check_class, None

                # The package existed, but no valid check class was found
                return None, {
                    'error': Exception(f"No AgentCheck subclass found in {module_full}"),
                    'traceback': None,
                }

        # No matching module found anywhere
        return None, {
            'error': Exception(f"No module named 'checks.corechecks.*.{check_name}'"),
            'traceback': None,
        }
