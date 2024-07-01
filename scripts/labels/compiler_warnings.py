# FIXME: Subsume into the newer label_tool package.
import argparse
import json
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
    """ Get CodeChecker labels for compiler warnings analyzer. """
    args = cli_args()

    url = 'https://clang.llvm.org/docs/DiagnosticsReference.html'

    http = urllib3.PoolManager()
    r = http.request('GET', url)
    data = r.data.replace(b'&nbsp;', b' ')
    root = ET.fromstring(data)

    with open(args.label_file, 'rb') as f:
        labels_data = json.load(f)

    labels = labels_data["labels"]

    for section in root.findall('.//*[@class="section"]'):
        perm = section.find('.//*[@title="Permalink to this headline"]')
        if perm is None:
            continue

        backref = section.find('.//*[@class="toc-backref"]')
        name = backref.text[2:].lower()  # Remove -W and convert to lower case.
        if name:
            checker_name = f"clang-diagnostic-{name}"
        else:
            checker_name = "clang-diagnostic"

        if checker_name not in labels:
            labels[checker_name] = []

        anchor = perm.attrib['href'].lstrip('#')
        if not any(lbl.startswith("doc_url:") for lbl in labels[checker_name]):
            labels[checker_name].append(f"doc_url:{url}#{anchor}")

        is_error = section.find('.//*[@class="error"]') is not None
        if not any(lbl.startswith("severity:")
                   for lbl in labels[checker_name]):
            if is_error:
                severity = "HIGH"
            else:
                severity = "MEDIUM"

            labels[checker_name].append(f"severity:{severity}")

    labels_data["labels"] = dict(sorted(labels.items()))
    with open(args.label_file, 'w', encoding='utf-8') as f:
        json.dump(labels_data, f, indent=2)


if __name__ == "__main__":
    main()
