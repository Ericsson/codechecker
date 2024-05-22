# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
import argparse
import functools
import json
import os
import subprocess
import sys
from multiprocess import Pool
from pathlib import Path
from typing import List, Tuple


def parse_args():
    """
    Initialize global variables based on command line arguments. These
    variables are global because get_results() uses them. That function is used
    as a callback which doesn't get this info as parameters.
    """
    parser = argparse.ArgumentParser(
        description="Fetch all reports of products")

    parser.add_argument(
        '--url',
        default='localhost:8001',
        help='URL of a CodeChecker server.')

    parser.add_argument(
        '--output',
        required=True,
        help='Output folder for generated JSON files.')

    parser.add_argument(
        '-j', '--jobs',
        default=1,
        type=int,
        help='Get reports in this many parallel jobs.')

    parser.add_argument(
        '--products',
        nargs='+',
        help='List of products to fetch reports for. By default, all products '
             'are fetched.')

    return parser.parse_args()


def __get_keys_from_list(out) -> List[str]:
    """
    Get all keys from a JSON list.
    """
    return map(lambda prod: next(iter(prod.keys())), json.loads(out))


def result_getter(args: argparse.Namespace):
    def get_results(product_run: Tuple[str, str]):
        product, run = product_run
        print(product, run)

        out, _ = subprocess.Popen([
                'CodeChecker', 'cmd', 'results', run,
                '-o', 'json',
                '--url', f'{args.url}/{product}'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE).communicate()

        reports = sorted(
            json.loads(out), key=lambda report: report['reportId'])

        run = run.replace('/', '_')
        with open(Path(args.output) / f'{product}_{run}.json', 'w',
                  encoding='utf-8') as f:
            json.dump(reports, f)

    return get_results


def get_all_products(url: str) -> List[str]:
    """
    Get all products from a CodeChecker server.

    :param url: URL of a CodeChecker server.
    :return: List of product names.
    """
    out, _ = subprocess.Popen(
        ['CodeChecker', 'cmd', 'products', 'list', '-o', 'json', '--url', url],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL).communicate()

    return __get_keys_from_list(out)


def dump_products(args: argparse.Namespace):
    for product in args.products:
        f = functools.partial(lambda p, r: (p, r), product)
        with subprocess.Popen([
                'CodeChecker', 'cmd', 'runs',
                '--url', f'{args.url}/{product}',
                '-o', 'json'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        ) as proc:
            runs = list(__get_keys_from_list(proc.stdout.read()))

            with Pool(args.jobs) as p:
                p.map(result_getter(args), map(f, runs))


def main():
    args = parse_args()

    os.makedirs(args.output, exist_ok=True)

    if not args.products:
        args.products = get_all_products(args.url)

    dump_products(args)

    return 0


if __name__ == '__main__':
    sys.exit(main())
