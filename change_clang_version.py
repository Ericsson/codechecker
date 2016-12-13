#!/usr/bin/env python

import json
import platform

with open('config/package_layout.json') as f:
    data = json.load(f)

if platform.system() == 'Linux':
    data['runtime']['analyzers']['clangsa'] = 'clang-3.8'
    data['runtime']['analyzers']['clang-tidy'] = 'clang-tidy-3.8'
if platform.system() == 'Darwin':
    data['runtime']['analyzers']['clangsa'] = 'clang'

with open('config/package_layout.json', 'w') as f:
    json.dump(data, f, indent=4)
