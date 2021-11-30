import argparse
import json
import re
import urllib3
import xml.etree.ElementTree as ET


def cli_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--label-file',
        required=True,
        help='Path to the label file which will be inserted the checker '
             'documentation URLs.')

    return parser.parse_args()


def main():
    """ Get CodeChecker labels for markdownlint analyzer. """
    args = cli_args()

    url = 'https://github.com/markdownlint/markdownlint/blob/v0.11.0/docs/RULES.md'
    raw_url = url \
        .replace("github.com", "raw.githubusercontent.com") \
        .replace("/blob", "")

    http = urllib3.PoolManager()
    r = http.request('GET', raw_url)
    lines = r.data.decode().split('\n')

    labels = {}
    rgx = re.compile(r"\s+\* \[(?P<name>MD\d+)[^\]]+\]\((?P<anchor>\S+)\)")
    for line in lines:
        m = rgx.match(line)
        if m:
            checker_name = m.group("name")
            anchor = m.group("anchor")
            if checker_name not in labels:
                labels[checker_name] = []

            labels[checker_name] = [
                f"doc_url:{url}{anchor}",
                "severity:STYLE"
            ]

    with open(args.label_file, 'w') as f:
        json.dump({
            "analyzer": "mdl",
            "labels": dict(sorted(labels.items()))
        }, f, indent=2)


if __name__ == "__main__":
    main()
