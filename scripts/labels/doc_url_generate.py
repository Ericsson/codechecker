# FIXME: Subsume into the newer label_tool/doc_url package!
import argparse
import json
import sys
import urllib3
import xml.etree.ElementTree as ET
from collections import OrderedDict


def clangsa(label_file):
    url = 'https://clang.llvm.org/docs/analyzer/checkers.html'

    http = urllib3.PoolManager()
    r = http.request('GET', url)
    root = ET.fromstring(r.data)

    checker_anchors = []
    for x in root.findall('.//{*}a[@title="Permalink to this headline"]'):
        checker_anchors.append(x.attrib['href'].lstrip('#'))

    with open(label_file, encoding='utf-8') as f:
        checkers = json.load(f)['labels'].keys()

    docs = {}
    for checker in checkers:
        c = checker.lower().replace('.', '-')
        # next() evaluates the generator immediately.
        # pylint: disable=cell-var-from-loop
        anchor = next(filter(
            lambda anchor: anchor.startswith(c), checker_anchors), None)

        if anchor:
            docs[checker] = f'{url}#{anchor}'

    return docs


def clang_tidy(label_file):
    url = 'https://clang.llvm.org/extra/clang-tidy/checks/list.html'

    http = urllib3.PoolManager()
    r = http.request('GET', url)
    root = ET.fromstring(r.data)

    checker_anchors = []
    for x in root.findall('.//{*}a[@class="reference external"]'):
        checker_anchors.append(x.attrib['href'])

    with open(label_file, encoding='utf-8') as f:
        checkers = json.load(f)['labels'].keys()

    url = url[:url.rfind('/') + 1]
    docs = {}
    for checker in checkers:
        # next() evaluates the generator immediately.
        # pylint: disable=cell-var-from-loop
        anchor = next(filter(
            lambda anchor: anchor.startswith(checker), checker_anchors), None)

        if anchor:
            docs[checker] = f'{url}{anchor}'

    return docs


def get_labels_with_docs(label_file, docs):
    with open(label_file, encoding='utf-8') as f:
        labels = json.load(f, object_pairs_hook=OrderedDict)

    for checker, label in labels['labels'].items():
        if checker in docs:
            while True:
                try:
                    x = next(filter(lambda x: x.startswith('doc_url'), label))
                    label.remove(x)
                except StopIteration:
                    break

            label.append(f'doc_url:{docs[checker]}')
        else:
            x = next(filter(lambda x: x.startswith('doc_url'), label), None)
            info = f'Previous URL: {x[x.find(":") + 1:]}' if x \
                else 'No previous URL.'

            print(
                f'Documentation URL not found for {checker}. {info}',
                file=sys.stderr)

        label.sort()

    return labels


analyzer_doc_getter = {
    'clangsa': clangsa,
    'clang-tidy': clang_tidy
}


def cli_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--label-file',
        required=True,
        help='Path to the label file which will be inserted the checker '
             'documentation URLs.')

    parser.add_argument(
        '--analyzer',
        required=True,
        choices=analyzer_doc_getter.keys(),
        help='Analyzer name that defines the format of the URL.')

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print the content of the resulting label file instead of '
             'modifying it.')

    return parser.parse_args()


def main():
    args = cli_args()

    docs = analyzer_doc_getter[args.analyzer](args.label_file)
    labels = get_labels_with_docs(args.label_file, docs)

    if args.dry_run:
        print(json.dumps(labels, indent=2))
    else:
        with open(args.label_file, 'w', encoding='utf-8') as f:
            json.dump(labels, f, indent=2)


if __name__ == '__main__':
    main()
