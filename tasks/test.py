# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

"""
High level testing tasks
"""
import os
import json
import mmap
import re

from termcolor import colored
from json.decoder import JSONDecodeError
from pylint import epylint

from invoke import task
from invoke.exceptions import Exit

from .utils import (
    get_repo_path,
    get_matching,
)

# We use `basestring` in the code for compat with python2 unicode strings.
# This makes the same code work in python3 as well.
try:
    basestring
except NameError:
    basestring = str

PROFILE_COV = "profile.cov"

PYLINT_RC = ".pylintrc"
FLAKE8_RC = ".flake8"

LINT_SKIP_PATTERNS = [
    r".*\/venv.*\/",
    r".*\/.tox\/",
]
UNLICENSED_EXT_PATTERNS = [
    r"LICENSE$",
    r"\..*$",
    r".*Gemfile(\.lock)?$",
    r".*Berksfile(\.lock)?$",
    r".*\.rb$",
    r".*\.txt$",
    r".*\.json$",
    r".*\.patch$",
    r".*\.yaml.*$",
    r".*\.md$",
    r".*\.ini$"
]


@task()
def test(ctx, targets=None, timeout=120):
    """
    Run all the tools and tests on the given targets. If targets are not specified,
    the value from `invoke.yaml` will be used.

    Example invokation:
        inv test --targets=./pkg/collector/check,./pkg/aggregator --race
    """
    if not targets:
        print("\n--- Running unit tests on agent code:")
        ctx.run("python -m pytest -v .", pty=True)
        print("\n--- Running unit tests on bundled checks:")
        test_wheels(ctx)
    else:
        for target in targets:
            print("\n--- Running unit tests on agent code:")
            ctx.run("python -m pytest -v {}".format(target), pty=True)


@task
def test_wheels(ctx):
    wheels = set()
    matches = get_matching(get_repo_path(), patterns=[r"^checks\/bundled\/.*\/tests\/.*\.py$"])

    success = True
    wheels = set([os.path.dirname(os.path.dirname(match)) for match in matches])
    for wheel in wheels:
        result = ctx.run('python -m pytest -v {}'.format(wheel), warn=True, pty=True)
        success = (success and True) if result.ok else False

@task
def lint_py(ctx, targets=None):
    args = "--rcfile={} --reports=y".format(get_repo_path(PYLINT_RC))
    files = get_matching(get_repo_path(), patterns=[r".*\.py$"], exclude_patterns=LINT_SKIP_PATTERNS)

    stdout, _ = epylint.py_run("{target} {args}".format(target=" ".join(files), args=args), return_std=True)

    try:
        msgs = json.load(stdout)
        for msg in msgs:
            if msg['type'].lower() == 'error':
                print(colored(json.dumps(msg, sort_keys=True, indent=4), "red"))
            else:
                print(colored(json.dumps(msg, sort_keys=True, indent=4), "green"))
        else:
            print(colored("Nice! No lint errors!", "green"))
    except JSONDecodeError:
        print(colored("Whoopsie Daisy! There was an issue linting your code!", "red"))

@task
def flake8(ctx, targets=None, branch=None):
    success = True

    if not targets:
        files = get_matching(get_repo_path(), patterns=[r".*\.py$"], reference=branch)
        result = ctx.run("flake8 --config={rc_file} {targets}".format(
            rc_file=get_repo_path(FLAKE8_RC),
            targets=' '.join(files)), pty=True)
        success = True if result.ok else False
    else:
        for target in targets.split(','):
            print("Checking {}...".format(target))
            result = ctx.run("flake8 --config={rc_file} {target}".format(
                rc_file=get_repo_path(FLAKE8_RC),
                target=target), pty=True)
            success = (success and True) if result.ok else False

    if success:
        print(colored("Nice! No flakes errors!", "green"))

@task
def lint_milestone(ctx):
    """
    Make sure PRs are assigned a milestone
    """
    pr_url = os.environ.get("CIRCLE_PULL_REQUEST")
    if pr_url:
        import requests
        pr_id = pr_url.rsplit('/')[-1]

        res = requests.get("https://api.github.com/repos/DataDog/datadog-unix-agent/issues/{}".format(pr_id))
        pr = res.json()
        if pr.get("milestone"):
            print("Milestone: %s" % pr["milestone"].get("title", "NO_TITLE"))
            return

        print("PR %s requires a milestone" % pr_url)
        raise Exit(code=1)

    # The PR has not been created yet
    else:
        print("PR not yet created, skipping check for milestone")

@task
def lint_teamassignment(ctx):
    """
    Make sure PRs are assigned a team label
    """
    pr_url = os.environ.get("CIRCLE_PULL_REQUEST")
    if pr_url:
        import requests
        pr_id = pr_url.rsplit('/')[-1]

        res = requests.get("https://api.github.com/repos/DataDog/datadog-agent/issues/{}".format(pr_id))
        issue = res.json()
        for label in issue.get('labels', {}):
            if re.match('team/', label['name']):
                print("Team Assignment: %s" % label['name'])
                return

        print("PR %s requires team assignment" % pr_url)
        raise Exit(code=1)

    # The PR has not been created yet
    else:
        print("PR not yet created, skipping check for team assignment")


@task
def lint_releasenote(ctx):
    """
    Lint release notes with Reno
    """

    # checking if a releasenote has been added/changed
    pr_url = os.environ.get("CIRCLE_PULL_REQUEST")
    if pr_url:
        import requests
        pr_id = pr_url.rsplit('/')[-1]

        # first check 'changelog/no-changelog' label
        res = requests.get("https://api.github.com/repos/DataDog/datadog-unix-agent/issues/{}".format(pr_id))
        issue = res.json()
        if any([l['name'] == 'changelog/no-changelog' for l in issue.get('labels', {})]):
            print("'changelog/no-changelog' label found on the PR: skipping linting")
            return

        # Then check that at least one note was touched by the PR
        url = "https://api.github.com/repos/DataDog/datadog-unix-agent/pulls/{}/files".format(pr_id)
        # traverse paginated github response
        while True:
            res = requests.get(url)
            files = res.json()
            if any([f['filename'].startswith("releasenotes/notes/") for f in files]):
                break

            if 'next' in res.links:
                url = res.links['next']['url']
            else:
                print("Error: No releasenote was found for this PR. Please add one using 'reno'.")
                raise Exit(code=1)

    # The PR has not been created yet, let's compare with master (the usual base branch of the future PR)
    else:
        branch = os.environ.get("CIRCLE_BRANCH")
        if branch is None:
            print("No branch found, skipping reno linting")
        else:
            if re.match(r".*/.*", branch) is None:
                print("{} is not a feature branch, skipping reno linting".format(branch))
            else:
                import requests

                # Then check that in the diff with master, at least one note was touched
                url = "https://api.github.com/repos/DataDog/datadog-unix-agent/compare/master...{}".format(branch)
                # traverse paginated github response
                while True:
                    res = requests.get(url)
                    files = res.json().get("files", {})
                    if any([f['filename'].startswith("releasenotes/notes/") for f in files]):
                        break

                    if 'next' in res.links:
                        url = res.links['next']['url']
                    else:
                        print("Error: No releasenote was found for this PR. Please add one using 'reno'.")
                        raise Exit(code=1)

    ctx.run("reno lint")

@task
def lint_filenames(ctx, branch=None):
    """
    Scan files to ensure there are no filenames too long or containing illegal characters
    """
    files = get_matching(get_repo_path(), reference=branch)
    failure = False

    print("Checking filenames for illegal characters")
    forbidden_chars = '<>:"\\|?*'
    for file in files:
        if any(char in file for char in forbidden_chars):
            print("Error: Found illegal character in path {}".format(file))
            failure = True

    print("Checking filename length")
    # Approximated length of the prefix of the repo during the windows release build
    prefix_length = 160
    # Maximum length supported by the win32 API
    max_length = 255
    for file in files:
        if prefix_length + len(file) > max_length:
            print("Error: path {} is too long ({} characters too many)".format(file, prefix_length + len(file) - max_length))
            failure = True

    if failure:
        raise Exit(code=1)


@task
def lint_licenses(ctx, branch=None):
    """
    Scan files to ensure there are no filenames too long or containing illegal characters
    """
    unlicensed = []
    LICENSE_CUE = b"# Unless explicitly stated otherwise all files in this repository are licensed"

    files = get_matching(get_repo_path(), exclude_patterns=UNLICENSED_EXT_PATTERNS, reference=branch)
    for f in files:
        try:
            with open(f, 'rb', 0) as fp, mmap.mmap(fp.fileno(), 0, access=mmap.ACCESS_READ) as s:
                if s.find(LICENSE_CUE) == -1:
                    unlicensed.append(f)
        except ValueError:
            unlicensed.append(f)

    if not unlicensed:
        print(colored('All good!', 'green'))
        return

    for f in unlicensed:
        print(colored("File {} is missing a license header".format(f), "red"))

    raise Exit(code=1)
