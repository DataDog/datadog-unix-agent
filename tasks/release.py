# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

"""
Release helper tasks
"""
import shutil
import sys
from datetime import date

from invoke import task, Failure
from invoke.exceptions import Exit

from git import Repo


@task
def add_prelude(ctx, version):
    res = ctx.run("reno new prelude-release-{0}".format(version))
    new_releasenote = res.stdout.split(' ')[-1].strip() # get the new releasenote file path
    repo = Repo('.')  # maybe this should be something else...

    with open(new_releasenote, "w") as f:
        f.write("""prelude:
    |
    Release on: {1}

    - Please refer to the `{0} tag on integrations-core <https://github.com/DataDog/integrations-core/blob/master/AGENT_CHANGELOG.md#datadog-agent-version-{2}>`_ for the list of changes on the Core Checks.

    - Please refer to the `{0} tag on process-agent <https://github.com/DataDog/datadog-process-agent/releases/tag/{0}>`_ for the list of changes on the Process Agent.\n""".format(version, date.today(), version.replace('.', '')))

    repo.index.add([new_releasenote])
    repo.index.commit("Add prelude for {} release".format(version))

@task
def update_changelog(ctx, new_version):
    """
    Quick task to generate the new CHANGELOG using reno when releasing a minor
    version (linux only).
    """
    new_version_int = list(map(int, new_version.split(".")))
    repo = Repo('.')  # maybe this should be something else...

    if len(new_version_int) != 3:
        print("Error: invalid version: {}".format(new_version_int))
        raise Exit(1)

    # let's avoid losing uncommitted change with 'git reset --hard'
    diffs = repo.index.diff(None)
    if diffs:
        print("Error: You have uncommitted change, please commit or stash before using update_changelog")
        return

    # make sure we are up to date
    repo.remotes.origin.fetch()  # git fetch

    # let's check that the tag for the new version is present (needed by reno)
    try:
        repo.tags[new_version]
    except IndexError as e:
        print("Missing '{}' git tag: mandatory to use 'reno'".format(new_version))
        raise

    # removing releasenotes from bugfix on the old minor.
    previous_minor = "%s.%s" % (new_version_int[0], new_version_int[1] - 1)
    logs = repo.git.log("{}.0...remotes/origin/{}.x".format(previous_minor, previous_minor), "--name-only")
    log_result = []
    for log in logs.splitlines():
        if 'releasenotes/notes/' in log:
            log_result.append(log)

    if log_result:
        repo.index.remove(log_result)  # make sure this applies --ignore-unmatch

    # generate the new changelog
    ctx.run("reno report \
            --ignore-cache \
            --earliest-version {}.0 \
            --version {} \
            --no-show-source > /tmp/new_changelog.rst".format(previous_minor, new_version))

    # reseting git
    repo.head.reset(index=True, working_tree=True)  # git reset --hard

    # merging to CHANGELOG.rst
    changelog = None
    with open('/tmp/new_changelog.rst', 'r') as fp:
        changelog = fp.read().splitlines()
    with open('CHANGELOG.rst', 'r+') as fp:
        # remove the old header start 4 bytes in
        changelog.append(changelog.read().splitlines()[4:])
        fp.seek(0)
        fp.write('\n'.join(changelog))
        fp.truncate()

    # commit new CHANGELOG
    repo.index.add(['CHANGELOG.rst'])
    repo.index.commit("Update CHANGELOG for {}".format(new_version))
