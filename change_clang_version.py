#!/usr/bin/env python

import json

data = None

with open('config/package_layout.json') as f:
    data = json.load(f)

data['runtime']['analyzers']['clangsa'] = 'clang-3.7'

with open('config/package_layout.json', 'w') as f:
    json.dump(data, f, indent=4)
