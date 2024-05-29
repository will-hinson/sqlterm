#!/usr/bin/env python
# pylint: disable=missing-module-docstring

import os
from typing import List

from setuptools import find_packages, setup

required_packages: List[str]
with open(
    os.path.join(os.path.dirname(__file__), "requirements.txt"), "r", encoding="utf-8"
) as requirements_file:
    required_packages = [
        requirement_entry.strip()
        for requirement_entry in requirements_file.readlines()
        if len(requirement_entry.strip()) > 0
        and not requirement_entry.strip().startswith("#")
    ]

setup(
    name="sqlterm",
    author="Will Hinson",
    version="0.2.0",
    url="https://github.com/will-hinson/sqlterm",
    description="A modern command-line client for SQL",
    packages=find_packages(),
    install_requires=required_packages,
    entry_points={"console_scripts": ["sqlterm = sqlterm.entrypoint:main"]},
)
