# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Fetch the list of official LLVM release versions."""
import os

from lxml import html
from selenium import webdriver
from selenium.webdriver.common.by import By as WebdriverBy

from ...output import error
from ...transformer import Version, Versions


def fetch_llvm_release_versions() -> Versions:
    """
    Downloads and returns the list of release versions (tags) for the
    LLVM Project from the official archive.
    """
    # Note: Schema for the page last checked for version 18.1.
    url = "https://releases.llvm.org"
    xpath = "*//table[@id=\"download\"]"

    try:
        os.environ["MOZ_HEADLESS"] = "1"

        # Unfortunately, a pure HTTP GET is not enough here, because the
        # download table is populated by an inline JavaScript which we can't
        # execute directly from Python code.
        with webdriver.Firefox() as wd:
            wd.get(url)
            table_src = wd.find_element(WebdriverBy.XPATH, xpath). \
                get_attribute("outerHTML")
            download_table = html.fromstring(table_src)
    except Exception:
        import traceback
        traceback.print_exc()

        error("Failed to download or parse page '%s'!", url)
        return []
    finally:
        try:
            del os.environ["MOZ_HEADLESS"]
        except KeyError:
            pass

    releases = [Version(r)
                for r in [r.text_content()
                          for r in download_table.findall(".//tr/td[2]")]
                if r not in ("Version", "Git",)]
    return releases
