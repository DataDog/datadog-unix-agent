"""
Invoke entrypoint, import here all the tasks we want to make available
"""
import os
from invoke import Collection

from . import release

from .test import test, lint_teamassignment, lint_releasenote, lint_milestone, lint_filenames, lint_py

# the root namespace
ns = Collection()

# add single tasks to the root
ns.add_task(test)
ns.add_task(lint_py)
ns.add_task(lint_teamassignment)
ns.add_task(lint_releasenote)
ns.add_task(lint_milestone)
ns.add_task(lint_filenames)

# add namespaced tasks to the root
ns.add_collection(release)

ns.configure({
    'run': {
        # workaround waiting for a fix being merged on Invoke,
        # see https://github.com/pyinvoke/invoke/pull/407
        'shell': os.environ.get('COMSPEC', os.environ.get('SHELL')),
        # this should stay, set the encoding explicitly so invoke doesn't
        # freak out if a command outputs unicode chars.
        'encoding': 'utf-8',
    }
})
