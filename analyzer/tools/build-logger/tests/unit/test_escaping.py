#!/usr/bin/env python3

import json
import os
import tempfile
import unittest
from . import BasicLoggerTest, empty_env, run_command, REPO_ROOT


backslash = "\\"
bell = "\a"
backspace = "\b"
tab = "\t"
newline = "\n"
verticaltab = "\v"
carrigereturn = "\r"

# The following 3 characters are below 0x20, so they need special treat.
# However, these are not *explicitly* escaped by the ldlogger.
ack = "\x06"
shiftin = "\x0F"
datalinkescape = "\x10"
escape = "\x1B"
formfeed = "\f"


class EscapingTests(BasicLoggerTest):
    def test_space(self):
        """Test if the space character is escaped in command-line defines."""
        logger_env = self.get_envvars()
        file = self.source_file
        binary = self.binary_file
        self.assume_successful_command(
            ["gcc", "-DVARIABLE=hello world", file, "-Werror", "-o", binary],
            logger_env,
        )
        self.assume_successful_command(
            [binary], env=empty_env, outs="--hello world--"
        )
        self.assert_json(
            command=fr'gcc -DVARIABLE=hello{backslash} world'
                    fr' {file} -Werror -o {binary}',
            file=file,
        )

    def test_quote(self):
        """Test if the quote character is escaped in command-line defines."""
        logger_env = self.get_envvars()
        file = self.source_file
        binary = self.binary_file
        self.assume_successful_command(
            ["gcc", '-DVARIABLE="hello"', file, "-Werror", "-o", binary],
            logger_env,
        )
        self.assume_successful_command(
            [binary], env=empty_env, outs='--"hello"--'
        )
        self.assert_json(
            command=fr'gcc -DVARIABLE={backslash}"hello{backslash}"'
                    fr' {file} -Werror -o {binary}',
            file=file,
        )

    def test_space_quote(self):
        """Test command-line defines containing both spaces and quotes."""
        logger_env = self.get_envvars()
        file = self.source_file
        binary = self.binary_file
        self.assume_successful_command(
            [
                "gcc",
                '-DVARIABLE=he says: "hello world"',
                file,
                "-Werror",
                "-o",
                binary,
            ],
            logger_env,
        )
        self.assume_successful_command(
            [binary], env=empty_env, outs='--he says: "hello world"--'
        )
        self.assert_json(
            command=fr'gcc -DVARIABLE=he{backslash} says:{backslash}'
                    fr' {backslash}"hello{backslash} world{backslash}" '
                    fr'{file} -Werror -o {binary}',
            file=file,
        )

    def test_space_backslashes(self):
        """
        Test command-line defines containing escape characters and quotes.
        """
        logger_env = self.get_envvars()
        file = self.source_file
        binary = self.binary_file
        self.assume_successful_command(
            [
                "gcc",
                fr'-DVARIABLE={backslash*4}built'
                fr'{backslash*2}ages "ago"{backslash*2}',
                file,
                "-Werror",
                "-o",
                binary,
            ],
            logger_env,
        )
        self.assume_successful_command(
            [binary],
            env=empty_env,
            outs=fr'--{backslash*2}built{backslash}ages "ago"{backslash}--',
        )
        self.assert_json(
            command=fr'gcc -DVARIABLE={backslash*8}built{backslash*4}ages'
                    fr'{backslash} {backslash}"ago{backslash}"{backslash*4}'
                    fr' {file} -Werror -o {binary}',
            file=file,
        )

    def test_defining_quotes(self):
        """
        Test if the quoted argument is still quoted within the c++
        source file after it's substituted by the preprocessor.
        In other words, the outermost quote should be preserved and
        result in a compile-time concatenated string in the printf().
        """
        fd, file = tempfile.mkstemp(
            suffix=".cpp", prefix="logger-test-source-", text=True
        )
        os.write(
            fd,
            bytes(
                """
#include <stdio.h>
int main() {
  printf("%s", "--" VARIABLE "--");
}
""",
                "utf-8",
            ),
        )
        try:
            logger_env = self.get_envvars()
            binary = self.binary_file
            self.assume_successful_command(
                ["gcc", '-DVARIABLE="abc"', file, "-Werror", "-o", binary],
                logger_env,
            )
            self.assume_successful_command(
                [binary], env=empty_env, outs="--abc--"
            )
            self.assert_json(
                command=fr'gcc -DVARIABLE={backslash}"abc{backslash}"'
                        fr' {file} -Werror -o {binary}',
                file=file,
            )
        finally:
            if os.path.isfile(file):
                os.remove(file)

    # Currently we don't escape correctly:
    # '\a', '\e', '\t', '\t', '\b', '\f', '\r', '\v', '\n'.
    @unittest.expectedFailure
    def test_control_characters(self):
        """
        Test if control-characters are escaped.
        Without escaping these we might end up in
        a malformed command-line invocation.
        """
        logger_env = self.get_envvars()
        file = self.source_file
        binary = self.binary_file
        self.assume_successful_command(
            [
                "gcc",
                fr'-DVARIABLE={bell}A{backspace}B{tab}'
                fr'C{newline}D{verticaltab}E{carrigereturn}',
                file,
                "-Werror",
                "-o",
                binary,
            ],
            logger_env,
        )
        self.assume_successful_command(
            [binary],
            env=empty_env,
            outs="--\aA\bB C--",
        )
        self.assert_json(
            command=fr'gcc -DVARIABLE={backslash}aA{backslash}bB{backslash}t'
                    fr'C{backslash}nD{backslash}vE{backslash}r'
                    fr' {file} -Werror -o {binary}',
            file=file,
        )

    # Currently we don't escape correctly:
    # '\a', '\e', '\t', '\t', '\b', '\f', '\r', '\v', '\n'.
    @unittest.expectedFailure
    def test_control_characters2(self):
        """
        Test the more esoteric control-characters.
        The 'Z' character demonstrates that the defined
        variable holds the right content even at the end.
        """

        logger_env = self.get_envvars()
        file = self.source_file
        binary = self.binary_file
        # FIXME: Why gets the formfeed character substituted by a regular
        #        space character?
        self.assume_successful_command(
            [
                "gcc",
                fr'-DVARIABLE={ack}{shiftin}'
                fr'{datalinkescape}{escape}{formfeed}Z',
                file,
                "-Werror",
                "-o",
                binary,
            ],
            logger_env,
        )
        self.assume_successful_command(
            [binary],
            env=empty_env,
            # FIXME: no formfeed, why?
            outs=fr'--{ack}{shiftin}{datalinkescape}{escape} Z--',
        )
        self.assert_json(
            command=fr'gcc -DVARIABLE={backslash}x06{backslash}x0F'
                    fr'{backslash}x10{backslash}e{backslash}fZ'
                    fr' {file} -Werror -o {binary}',
            file=file,
        )

    def test_email(self):
        """
        Test that a quoted email addess can be passed as a command-line define.
        """
        logger_env = self.get_envvars()
        file = self.source_file
        binary = self.binary_file
        self.assume_successful_command(
            [
                "gcc",
                fr'-DVARIABLE="my-email@address.com"',
                file,
                "-Werror",
                "-o",
                binary,
            ],
            logger_env,
        )
        self.assume_successful_command(
            [binary],
            env=empty_env,
            outs=fr'--"my-email@address.com"--',
        )
        self.assert_json(
            command=fr'gcc -DVARIABLE='
                    fr'{backslash}"my-email@address.com{backslash}"'
                    fr' {file} -Werror -o {binary}',
            file=file,
        )

    def test_valid_json_even_on_error(self):
        """Build failures should be ignored during logging."""
        logger_env = self.get_envvars()

        retcode, stdout, stderr = run_command(
            cmd=["gcc"], env=logger_env, cwd=REPO_ROOT)
        self.assertEqual(stdout, "")
        self.assertIn("no input files", stderr)
        self.assertNotEqual(retcode, 0)

        # Expected an empty log file.
        parsed_json = json.loads(self.read_actual_json())
        self.assertTrue(isinstance(parsed_json, list))
        self.assertEqual(len(parsed_json), 0)
