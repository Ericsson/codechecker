# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Transform URLs based on patterns and heuristics."""
import re
from typing import Callable, Dict, Iterable, List, Optional, Union, cast

import packaging.version
from packaging.version import Version

from .util import lower_bound


Versions = List[Version]
LazyVersions = Union[Versions, Callable[[], Versions]]


class ReplacePatternApplicator:
    """
    Allows building strings by replacing `<VARIABLES>` in a pre-determined
    pattern via the `__call__` operator.
    """

    placeholder_re = re.compile(r'<(.*?)>')

    def __init__(self, pattern: str):
        self._pattern = pattern
        self._placeholder_matches = list(
            self.placeholder_re.finditer(self._pattern))

    def __repr__(self) -> str:
        return f"{self.__class__.__module__}." \
            f"{self.__class__.__qualname__}" \
            f"(\"{self._pattern}\")"

    def __call__(self, **values) -> str:
        """
        Fills the placeholders in the `pattern` with the values specified in
        `values`.
        The values are specified case-insensitive.
        """
        r = str(self._pattern)
        for key, (begin, end) in map(lambda m: (m.group(1), m.span(1)),
                                     reversed(self._placeholder_matches)):
            r = r[:begin - 1] + values[key.lower()] + r[end + 1:]

        return r


class PerReleaseRules:
    """
    Implements the logic for generating fixed documentation URLs based
    on a rewriting patterns for cases where the requested documentation might
    exist in an older release of the software.
    """

    def __init__(self, releases: LazyVersions):
        """
        Initialises the data structures for the release-based fixer.

        A list of existing releases to check is required, either in an already
        acquired, or in a lazy-loadable format.
        """
        if isinstance(releases, list):
            self._releases = releases
            self._releases.sort()
            self._releases.reverse()
        else:
            self._releases = None
            self._fetch_releases = releases

        self._rules: Dict[Union[Version,
                                packaging.version.InfinityType,
                                packaging.version.NegativeInfinityType],
                          Optional[Callable]] = {}
        self._rules[packaging.version.NegativeInfinity] = None
        self._rules[packaging.version.Infinity] = None

    @property
    def releases(self) -> Versions:
        if not self._releases and self._fetch_releases:
            self._releases = self._fetch_releases()
            self._releases.sort()
            self._releases.reverse()
        return cast(Versions, self._releases)

    def add_rule(self, rule: Optional[Union[str, Callable]],
                 min_: Optional[Version] = None):
        """
        Registers `rule` to be the fixer's rewrite rule applied if the
        attempted version satisfies ``min_ <= V``.

        If `min_` is unset, it is understood as the hypothetical minimum
        version when rewriting, i.e., `releases()[0]`.
        Specify `None` as  `rule` to turn off rule application for an interval
        of versions.

        `rule` can be either a `str`, in which placeholders, in the format of
        ``<KEY>`` (e.g., ``<VERSION>``) are rewritten (see `__call__`, and
        `_Rule.__call__`), or a callback function, which receives the arguments
        of `__call__` and is expected to produce a `str` result.
        """
        self._rules[min_ or packaging.version.NegativeInfinity] = \
            ReplacePatternApplicator(rule) if isinstance(rule, str) \
            else rule

    def generate_url(self, version: Version, **opts: str) -> Optional[str]:
        """
        Generates an attemptible documentation URL for the given `version`
        based on the input `opts` that are applied to the found rewriting rule
        (see `add_rule()`).
        """
        release_bound = lower_bound(sorted(self._rules.keys()), version) \
            or packaging.version.NegativeInfinity
        rule_for_release = self._rules[release_bound]
        if not rule_for_release:
            return None

        attempt = rule_for_release(version=str(version), **opts)
        return attempt

    def generate_urls(self, **opts: str) -> Iterable[str]:
        """
        Generates attemptible older documentation URL based on the input `opts`
        that are applied to the rewriting rules (see `add_rule()`).
        """
        for release in self.releases:
            attempt = self.generate_url(release, **opts)
            if attempt:
                yield attempt

    def __call__(self, check: Callable[[str], bool], **opts: str) \
            -> Optional[str]:
        """
        Performs the attempt at creating a verifiable and valid fixed older
        documentation URL based on the input `opts` that are applied to the
        rewriting rules (see `add_rule()`).

        The results are intermittently checked by the provided `check`
        callback, and the first `True` result's input is returned.
        """
        for attempt in self.generate_urls(**opts):
            if check(attempt):
                return attempt
        return None
