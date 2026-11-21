# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""Regression tests for configuration files selected via the environment."""

import argparse
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from codechecker_client.cli import cmd, store
from codechecker_common import cli, cmd_config
from codechecker_common.cli_commands import version


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.config = os.path.join(self.directory.name, 'codechecker.json')
        self.environment = patch.dict(os.environ, {
            'CC_CONFIG_FILE': self.config,
            'CONFIG_HOST': 'https://example.com:9090',
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def write_config(self, config):
        with open(self.config, 'w', encoding='utf-8') as output:
            json.dump(config, output)

    def run_command(self, arguments, target, expected_code=0,
                    expect_handler=True):
        """Exercise both parsing passes without connecting to a server."""
        with patch.object(cli, 'configure_utf8_output'), \
                patch.object(cli, 'get_data_files_dir_path',
                             return_value=os.environ['CC_DATA_FILES_DIR']), \
                patch.object(cli, 'discover_subcommands', return_value={
                    'cmd': cmd.__name__, 'store': store.__name__,
                    'version': version.__name__}), \
                patch('sys.argv', ['CodeChecker'] + arguments), \
                patch(target, return_value=0) as handler:
            with self.assertRaises(SystemExit) as result:
                cli.main()
            self.assertEqual(result.exception.code, expected_code)
            if expected_code or not expect_handler:
                handler.assert_not_called()
                return None
            return handler.call_args.args[0]

    def test_product_url(self):
        self.write_config({'cmd': {'runs': [
            '--url=$CONFIG_HOST/MyProduct']}})
        args = self.run_command(
            ['cmd', 'runs'],
            'codechecker_client.cmd_line_client.handle_list_runs')
        self.assertEqual(args.product_url,
                         'https://example.com:9090/MyProduct')
        self.assertFalse(hasattr(args, 'server_url'))

    def test_server_url(self):
        self.write_config({'cmd': {'products': {'list': [
            '--url=$CONFIG_HOST']}}})
        args = self.run_command(
            ['cmd', 'products', 'list'],
            'codechecker_client.product_client.handle_list_products')
        self.assertEqual(args.server_url, 'https://example.com:9090')
        self.assertFalse(hasattr(args, 'product_url'))

    def test_store(self):
        self.write_config({'store': ['--url=$CONFIG_HOST/MyProduct']})
        args = self.run_command(['store', self.directory.name],
                                'codechecker_client.cli.store.main')
        self.assertEqual(args.product_url,
                         'https://example.com:9090/MyProduct')

    def test_explicit_config_precedence(self):
        self.write_config({'cmd': {'runs': ['--url=environment/Product']}})
        explicit = os.path.join(self.directory.name, 'explicit.json')
        with open(explicit, 'w', encoding='utf-8') as output:
            json.dump({'cmd': {'runs': ['--url=explicit/Product']}}, output)
        for option in (['--config', explicit], ['--config=' + explicit]):
            with self.subTest(option=option):
                args = self.run_command(
                    ['cmd', 'runs'] + option,
                    'codechecker_client.cmd_line_client.handle_list_runs')
                self.assertEqual(args.product_url, 'explicit/Product')

    def test_explicit_argument_order(self):
        self.write_config({'cmd': {'runs': ['--url=config/Product']}})
        for option in (['--config', self.config],
                       ['--config=' + self.config]):
            for before, expected in ((True, 'config/Product'),
                                     (False, 'cli/Product')):
                with self.subTest(option=option, before=before):
                    url = ['--url=cli/Product']
                    arguments = url + option if before else option + url
                    args = self.run_command(
                        ['cmd', 'runs'] + arguments,
                        'codechecker_client.cmd_line_client.handle_list_runs')
                    self.assertEqual(args.product_url, expected)

    def test_repeated_explicit_config_uses_last_position(self):
        self.write_config({'cmd': {'runs': ['--url=config/Product']}})
        args = self.run_command(
            ['cmd', 'runs', '--config=missing.json', '--url=cli/Product',
             '--config', self.config],
            'codechecker_client.cmd_line_client.handle_list_runs')
        self.assertEqual(args.product_url, 'config/Product')
        self.assertEqual(args.config_file, self.config)
        cmd_config.check_config_file(args)

    def test_explicit_config_ignores_missing_environment_file(self):
        self.write_config({'cmd': {'runs': ['--url=config/Product']}})
        with patch.dict(os.environ, {'CC_CONFIG_FILE': 'missing.json'}):
            for option in (['--config', self.config],
                           ['--config=' + self.config]):
                with self.subTest(option=option):
                    args = self.run_command(
                        ['cmd', 'runs'] + option,
                        'codechecker_client.cmd_line_client.handle_list_runs')
                    self.assertEqual(args.product_url, 'config/Product')
                    self.assertEqual(args.config_file, self.config)
                    cmd_config.check_config_file(args)

    def test_environment_config_is_appended(self):
        self.write_config({'cmd': {'runs': ['--url=config/Product']}})
        args = self.run_command(
            ['cmd', 'runs', '--url=cli/Product'],
            'codechecker_client.cmd_line_client.handle_list_runs')
        self.assertEqual(args.product_url, 'config/Product')

    def test_missing_section(self):
        self.write_config({'analyze': ['--clean']})
        args = self.run_command(
            ['cmd', 'runs'],
            'codechecker_client.cmd_line_client.handle_list_runs')
        self.assertEqual(args.product_url, 'localhost:8001/Default')

    def test_missing_file(self):
        parser = argparse.ArgumentParser()
        cmd_config.add_option(parser)
        with self.assertRaises(FileNotFoundError):
            cmd_config.process_config_file(parser.parse_args([]), 'store')

    def test_yaml(self):
        config = os.path.join(self.directory.name, 'codechecker.yaml')
        with open(config, 'w', encoding='utf-8') as output:
            output.write('cmd:\n  runs:\n    - --url=example.com/Product\n')
        with patch.dict(os.environ, {'CC_CONFIG_FILE': config}):
            args = self.run_command(
                ['cmd', 'runs'],
                'codechecker_client.cmd_line_client.handle_list_runs')
        self.assertEqual(args.product_url, 'example.com/Product')

    def test_no_environment_config(self):
        with patch.dict(os.environ, {'CC_CONFIG_FILE': ''}):
            args = self.run_command(
                ['cmd', 'products', 'list'],
                'codechecker_client.product_client.handle_list_products')
        self.assertEqual(args.server_url, 'localhost:8001')

    def test_existing_config_sections(self):
        self.write_config({
            'analyze': ['--clean'], 'parse': ['--trim-path-prefix=/tmp'],
            'server': ['--port=9090'], 'store': ['--name=test'],
        })
        parser = argparse.ArgumentParser()
        cmd_config.add_option(parser)
        args = parser.parse_args([])
        for command, expected in (
                ('analyze', ['--clean']),
                ('parse', ['--trim-path-prefix=/tmp']),
                ('server', ['--port=9090']),
                ('store', ['--name=test']),
                ('check', ['--clean', '--trim-path-prefix=/tmp'])):
            with self.subTest(command=command):
                self.assertEqual(
                    cmd_config.process_config_file(args, command), expected)

    def test_missing_cmd_actions(self):
        for config, commands in (
                ({}, ['runs']),
                ({'cmd': {}}, ['runs']),
                ({'cmd': {'products': {}}}, ['products', 'list']),
                ({'cmd': {}}, ['products', 'list'])):
            with self.subTest(config=config, commands=commands):
                self.assertEqual(cmd_config.get_cmd_options(config, commands),
                                 [])

    def test_malformed_cmd_configuration(self):
        for config, commands in (
                ([], ['runs']),
                ({'cmd': []}, ['runs']),
                ({'cmd': None}, ['runs']),
                ({'cmd': 'invalid'}, ['runs']),
                ({'cmd': {'products': []}}, ['products', 'list']),
                ({'cmd': {'runs': {}}}, ['runs']),
                ({'cmd': {'runs': None}}, ['runs']),
                ({'cmd': {'runs': '--url=example.com/Product'}}, ['runs']),
                ({'cmd': {'runs': [42]}}, ['runs']),
                ({'cmd': {'runs': [{'--url': 'example.com'}]}}, ['runs'])):
            with self.subTest(config=config, commands=commands):
                with self.assertRaisesRegex(ValueError, 'must be'):
                    cmd_config.get_cmd_options(config, commands)

    def test_empty_cmd_configuration(self):
        for config in (None, {'cmd': {'runs': []}}):
            with self.subTest(config=config):
                self.assertEqual(cmd_config.get_cmd_options(config, ['runs']),
                                 [])

    def test_config_errors_are_cli_errors(self):
        target = 'codechecker_client.cmd_line_client.handle_list_runs'
        for option in ([], ['--config', self.config],
                       ['--config=' + self.config]):
            with self.subTest(option=option):
                output = io.StringIO()
                with redirect_stdout(output), redirect_stderr(output):
                    self.run_command(['cmd', 'runs'] + option, target, 1)
                self.assertIn('does not exist', output.getvalue())
                self.assertNotIn('Traceback', output.getvalue())

        self.write_config({'cmd': {'runs': '--url=example.com'}})
        output = io.StringIO()
        with redirect_stdout(output), redirect_stderr(output):
            self.run_command(['cmd', 'runs'], target, 1)
        self.assertIn("'cmd.runs' must be a list of strings",
                      output.getvalue())
        self.assertNotIn('Traceback', output.getvalue())

    def test_all_cmd_action_paths(self):
        root = cli.ArgumentParser(prog='CodeChecker')
        subcommands = root.add_subparsers()
        cli.add_subcommand(subcommands, 'cmd', cmd.__name__)
        parser = subcommands.choices['cmd']
        paths = []

        def check_paths(current, path):
            for action in current._actions:  # pylint: disable=protected-access
                # Subparser choices map action names to their parsers.
                if not isinstance(action.choices, dict):
                    continue
                for name, child in action.choices.items():
                    child_path = path + [name]
                    if child.get_default('func') is not None:
                        self.assertEqual(
                            child.get_default('config_commands'), child_path)
                        paths.append(child_path)
                    check_paths(child, child_path)

        check_paths(parser, [])
        self.assertIn(['products', 'list'], paths)
        self.assertIn(['components', 'list'], paths)
        self.assertIn(['token', 'list'], paths)
        self.assertIn(['filter-preset', 'list'], paths)
        self.assertIn(['runs'], paths)

    def test_command_group_shows_help(self):
        self.write_config({'cmd': {'components': {
            'list': ['--url=example.com/Product']}}})
        with redirect_stdout(io.StringIO()):
            self.run_command(['cmd', 'components'],
                             'codechecker_client.source_component_client.'
                             'handle_list_components', expect_handler=False)

    def test_non_network_command_ignores_missing_config(self):
        self.run_command(['version'],
                         'codechecker_common.cli_commands.version.main')
