from setuptools import setup, find_packages

# io.open is needed for projects that support Python 2.7
# Python 3 only projects can skip this import
from io import open

# Get the long description from the README file
with open('README.md', encoding='utf-8', errors="ignore") as f:
    long_description = f.read()

api_version = '6.38.0-dev1'

setup(
    name='codechecker_api_shared',
    version=api_version,
    description='Shared API stub types package for the CodeChecker API.',
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

    project_urls={  # Optional
        'Bug Reports': 'https://github.com/Ericsson/codechecker/issues',
        'Source': 'https://github.com/Ericsson/codechecker/tree/master/web/api',
    },
)
