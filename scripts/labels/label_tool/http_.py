# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""HTTP connections and communication."""
import datetime
from http import HTTPStatus as HTTPStatusCode  # pylint: disable=unused-import
from typing import Dict, Optional, Union, Tuple
import urllib.parse

from lxml import html
import urllib3

from .output import trace


Response = urllib3.response.BaseHTTPResponse
URL = Union[str, urllib.parse.ParseResult]


class HTMLAcquirer:
    """
    Wrapper class that exposes fetching HTML pages over HTTP.
    """

    def __init__(self):
        self._pool = urllib3.PoolManager()

    def _get_url_raw(self, url: str) -> Response:
        """
        Downloads the contents of `url` and returns the raw HTTP response.
        Appropriate HTTP Redirects, which would be respected by the user's
        browser, are also transparently respected by this method.

        Notes
        -----
        By default, urrlib3 will retry requests 3 times and follow up to
        3 redirects.
        """
        trace("HTTP GET '%s'", url)
        return self._pool.request("GET", url)

    def get_url(self, url: URL) -> Response:
        """
        Downloads the content of `url` and returns the raw HTTP response.
        """
        if isinstance(url, urllib.parse.ParseResult):
            url = url.geturl()
        return self._get_url_raw(url)

    def _get_dom_raw(self, url: str) -> Optional[html.HtmlElement]:
        """
        Downloads the content of `url`.
        If the download is successful, parses the obtained HTML and returns the
        parsed `ElementTree` corresponding to its DOM.
        """
        response = self._get_url_raw(url)
        dom = html.fromstring(response.data) if response.data else None
        return dom

    def get_dom(self, url: URL) -> Optional[html.HtmlElement]:
        """
        Downloads the content of `url`.
        If the download is successful, parses the obtained HTML and returns the
        parsed `ElementTree` corresponding to its DOM.
        """
        if isinstance(url, urllib.parse.ParseResult):
            url = url.geturl()
        return self._get_dom_raw(url)

    def split_anchor(self, url: URL) -> Tuple[str, str]:
        if isinstance(url, str) and '#' not in url:
            return url, ""

        url_s = url if isinstance(url, urllib.parse.ParseResult) \
            else urllib.parse.urlparse(url)
        if not url_s.fragment and isinstance(url, str):
            return url, ""

        # The `_replace()` method will return a new ParseResult object...
        return url_s._replace(fragment="").geturl(), str(url_s.fragment) \
            if url_s.fragment else ""


class CachingHTMLAcquirer(HTMLAcquirer):
    """
    Wrapper class that exposes fetching and caching results of querying HTML
    pages over HTTP.
    """

    DefaultCacheSize = 16
    CacheType = Tuple[Response, Optional[html.HtmlElement]]

    def __init__(self, cache_size: int = DefaultCacheSize):
        super().__init__()
        self._cache_capacity = cache_size
        self._cache: Dict[str, CachingHTMLAcquirer.CacheType] = dict()
        self._cache_lru: Dict[str, datetime.datetime] = dict()

    def get_url(self, url: URL) -> Response:
        """
        Downloads the content of `url` after stripping the HTML anchor off of
        the request, and returns the raw HTTP response.
        """
        url, _ = self.split_anchor(url)
        cached = self._cache_get(url)
        if not cached:
            response = self._get_url_raw(url)
            dom = html.fromstring(response.data) if response.data else None
            cached = self._cache_set(url, (response, dom,))

        response, _ = cached
        return response

    def get_dom(self, url: URL) -> Optional[html.HtmlElement]:
        """
        Downloads the content of `url` after stripping the HTML anchor off of
        the request.
        If the download is successful, or the page is already in the cache,
        parses the obtained HTML and returns the parsed `ElementTree`
        corresponding to its DOM.
        """
        url, _ = self.split_anchor(url)
        cached = self._cache_get(url)
        if not cached:
            self.get_url(url)  # Populates the cache, if needed.
            cached = self._cache_get(url)
            if not cached:
                return None

        _, dom = cached
        return dom

    def _cache_get(self, k: str) -> Optional[CacheType]:
        try:
            o = self._cache[k]
            self._cache_lru[k] = datetime.datetime.now()
            return o
        except KeyError:
            return None

    def _cache_set(self, k: str, v: CacheType) -> CacheType:
        cache_hit = k in self._cache
        if self._cache_capacity > 0 and not cache_hit:
            while len(self._cache) >= self._cache_capacity:
                del_k = min(self._cache_lru, key=self._cache_lru.__getitem__)
                del self._cache[del_k]
                del self._cache_lru[del_k]

        self._cache[k] = v
        self._cache_lru[k] = datetime.datetime.now()
        return v
