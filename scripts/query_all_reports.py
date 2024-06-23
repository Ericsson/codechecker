import argparse
import functools
import json
import os
import subprocess
import sys
from multiprocessing import Pool
from pathlib import Path

URL = None
OUTPUT_FOLDER = None
JOBS = None

def init_globals():
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
        help="Get reports in this many parallel jobs.")

    args = parser.parse_args()

    global URL
    global OUTPUT_FOLDER
    global JOBS

    URL = args.url
    OUTPUT_FOLDER = args.output
    JOBS = args.jobs

def get_keys_from_list(out):
    return map(lambda prod: next(iter(prod.keys())), json.loads(out))

def get_results(args):
    product, run = args
    print(product, run)

    out, _ = subprocess.Popen([
            'CodeChecker', 'cmd', 'results', run,
            '-o', 'json',
            '--url', f'{URL}/{product}'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE).communicate()

    reports = sorted(json.loads(out), key=lambda report: report['reportId'])

    run = run.replace('/', '_')
    with open(Path(OUTPUT_FOLDER) / f'{product}_{run}.json', 'w') as f:
        json.dump(reports, f)

def main():
    init_globals()

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    out, _ = subprocess.Popen(
        ['CodeChecker', 'cmd', 'products', 'list', '-o', 'json', '--url', URL],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE).communicate()

    products = get_keys_from_list(out)

    for product in products:
        f = functools.partial(lambda p, r: (p, r), product)
        with subprocess.Popen([
                'CodeChecker', 'cmd', 'runs',
                '--url', f'{URL}/{product}',
                '-o', 'json'],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        ) as proc:
            runs = list(get_keys_from_list(proc.stdout.read()))

            with Pool(5) as p:
                p.map(get_results, map(f, runs))

    return 0

if __name__ == '__main__':
    sys.exit(main())
