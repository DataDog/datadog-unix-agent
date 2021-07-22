# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from os import path

from setuptools import setup

HERE = path.dirname(path.abspath(__file__))

# Get version info
ABOUT = {}
with open(path.join(HERE, 'datadog_checks', 'ibm_was', '__about__.py')) as f:
    exec(f.read(), ABOUT)

# Get the long description from the README file
with open(path.join(HERE, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


CHECKS_BASE_REQ = 'datadog_checks_base'


setup(
    name='datadog-ibm_was',
    version=ABOUT['__version__'],
    description='The IBM WAS check',
    long_description=long_description,
    long_description_content_type='text/markdown',
    keywords='datadog agent aix ibm_was check',
    # The project's main homepage.
    url='https://github.com/DataDog/datadog-unix-agent',
    # Author details
    author='Datadog',
    author_email='packages@datadoghq.com',
    # License
    license='BSD-3-Clause',
    # See https://pypi.org/classifiers
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Topic :: System :: Monitoring',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3.8',
    ],
    # The package we're going to ship
    packages=['datadog_checks.ibm_was'],
    # Run-time dependencies
    install_requires=[CHECKS_BASE_REQ],
    # Extra files to ship with the wheel package
    include_package_data=True,
)
