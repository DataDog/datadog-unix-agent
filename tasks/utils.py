# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import re

from git import Repo


def get_git_files(repo_path='.', reference=None):
    repo = Repo(repo_path)
    if not reference:
        reference = repo.active_branch.name
    head = getattr(repo.heads, reference)
    trees = [head.commit.tree]

    files = []
    while trees:
        current_tree = trees.pop()
        for blob in current_tree.blobs:
            files.append(blob.path)

        for tree in current_tree.trees:
            trees.append(tree)

    return files

def get_matching(path, patterns=[], exclude_patterns=[], reference=None):
    git_files = get_git_files(reference=reference)

    matching = []
    for f in git_files:
        matches = [re.search(pattern, f) for pattern in exclude_patterns]
        if any(matches):
            continue

        matches = [re.search(pattern, f) for pattern in patterns]
        if patterns and not any(matches):
            continue

        matching.append(f)

    return matching
