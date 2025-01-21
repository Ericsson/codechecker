from setuptools import setup, find_packages

# io.open is needed for projects that support Python 2.7
# Python 3 only projects can skip this import
from io import open

# Get the long description from the README file
with open('README.md', encoding='utf-8', errors="ignore") as f:
    long_description = f.read()

api_version = '6.59.0'

setup(
    name='codechecker_api',
    version=api_version,
    author='CodeChecker Team (Ericsson)',
    description='Generated Python compatible API stubs for CodeChecker.',
    long_description_content_type='text/markdown',
    long_description=long_description,
    url='https://github.com/Ericsson/codechecker',

    classifiers=[  # Optional
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',

        'Intended Audience :: Developers',
        # These classifiers are *not* checked by 'pip install'. See instead
        # 'python_requires' below.
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
    ],

    keywords='codechecker thrift api library',

    packages=find_packages(where='.'),  # Required

    python_requires='>=2.7,',
    install_requires=['thrift==0.13.0'],

    project_urls={
        'Bug Reports': 'https://github.com/Ericsson/codechecker/issues',
        'Source': 'https://github.com/Ericsson/codechecker/tree/master/web/api',
    },
)
