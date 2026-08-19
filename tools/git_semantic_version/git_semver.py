#!/bin/env python
import re
import sys
import os

import git

def get_commits(target_dir):
    repo = git.Repo(".", search_parent_directories=True)
    print(repo)
    commits = repo.iter_commits(paths=["--", os.path.abspath(target_dir)])
    commits = list(commits)
    commits.reverse()
    return commits

def _get_version_triplet(commits, initial=(0, 0, 0)):
    major, minor, patch = initial
    for commit in commits:
        message_type = re.sub(r'\(.*\)', '', commit.summary.split(":")[0]).replace(" ", "")
        if major > 0:
            if "!" in message_type or "BREAKING-CHANGE" in commit.trailers_dict:
                major += 1
                minor = 0
                patch = 0
            elif message_type == "feat":
                minor += 1
                patch = 0
            else:
                patch += 1
        else:
            if "!" in message_type or message_type == "feat" or "BREAKING-CHANGE" in commit.trailers_dict:
                minor += 1
                patch = 0
            else:
                patch += 1

    return (major, minor, patch)

def get_version_triplet(target_dir):
    commits = get_commits(target_dir)
    return _get_version_triplet(commits)

def get_version_string(target_dir="."):
    try:
        repo = git.Repo(".", search_parent_directories=True)
        version = ".".join([str(v) for v in get_version_triplet(target_dir)])
    except (git.exc.InvalidGitRepositoryError, git.exc.NoSuchPathError):
        if os.path.exists("PKG-INFO"):
            with open("PKG-INFO") as f:
                for line in f:
                    if line.startswith("Version:"):
                        return line.split(":", 1)[1].strip()
        else:
            version = "unknown"
    return version

def main():
    if sys.argv:
        target_dir = sys.argv[1]
    else:
        target_dir = "."
    return get_version_string(target_dir)

def set_semver(dist):
    dist.metadata.version = get_version_string()

if __name__ == "__main__":
    print(main())
