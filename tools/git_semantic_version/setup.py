import os
import sys

from setuptools import setup

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import git_semver

setup(
    version=git_semver.get_version_string()
)
