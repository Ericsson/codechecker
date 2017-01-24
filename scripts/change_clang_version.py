#!/usr/bin/env python

import json
import os
import platform
import sys

cfg_file = os.path.join(sys.argv[1], "config", "package_layout.json")

with open(cfg_file, "r+") as f:
    data = json.load(f)

    if platform.system() == 'Linux':
        data['runtime']['analyzers']['clangsa'] = 'clang-3.8'
        data['runtime']['analyzers']['clang-tidy'] = 'clang-tidy-3.8'
    if platform.system() == 'Darwin':
        data['runtime']['analyzers']['clangsa'] = 'clang'
    f.seek(0)
    json.dump(data, f, indent=4)
