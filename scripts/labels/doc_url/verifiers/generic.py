# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Implements the logic for generic verification of documentation URLs.
"""
from typing import Iterable, Optional, Tuple, cast

from lxml import html
import lxml.etree
import urllib3

from ... import http_ as http
from ...output import error, trace
from ...util import Ternary
from .status import Status


Outcome = Tuple[Status, Optional[http.Response]]


class Base:
    kind = "abstract"

    def __init__(self, analyser: str):
        self.analyser = analyser

    def skip(self, _checker: str, _url: str) -> Status:
        """
        Returns `Status.OK` if the current verifier is capable of verifying the
        `checker`.
        `Status.SKIP` is returned in case the `checker` is unverifiable due to
        a pattern, and `Status.MISSING` is returned if it is unverifiable due
        to its lack of `url`.
        """
        return Status.OK

    def verify(self, _checker: str, _url: str) -> Outcome:
        """
        Verifies that the documentation page at `url` is available and relevant
        for the `checker` checker.

        Subclasses must override this method and provide an implementation.
        """
        return Status.UNKNOWN, None

    def reset(self, _checker: str, _url: str) -> Optional[str]:
        """
        Attempts to reset a potentially fixed (e.g., downgraded) documentation
        URL to its rawest upstream version.
        There are no guarantees that the method here returns a valid,
        user-accessible URL.
        This method is used, when requested, to essentially "undo" the results
        of `try_fix`.

        This class does not implement any link-resetting capability.
        Subclasses might override this method and provide an implementation.
        """
        return None

    def try_fix(self, _checker: str, _url: str) -> Optional[str]:
        """
        Attempts to fix the documentation supposedly available, but in fact
        missing from `url` for `checker` to some alternative version that is
        still available to users.
        A common reason for the disappearance of current `url`s is the
        removal of checks, after which the previously up-to-date URLs would
        cause errors if accessed.

        This class does not implement any link-fixing capability.
        Subclasses might override this method and provide an implementation.
        """
        return None


class HTTPStatusCodeVerifier(Base):
    """
    Generic URL verifier that only checks whether the URL returns a valid
    HTTP status that indicates the URL resolves to a documentation accessible
    by the user.

    This class does not allow downgrading the documentation URL to an earlier
    version.
    """

    kind = "webpage"

    """
    HTTP Response status codes that indicate that the webpage is
    deterministically available to the request.
    """
    Ok = {http.HTTPStatusCode.OK,
          http.HTTPStatusCode.NON_AUTHORITATIVE_INFORMATION,
          }
    """
    HTTP Response status codes that indicate that the webpage is not or
    no longer available to requestors.
    """
    NotOk = {http.HTTPStatusCode.BAD_REQUEST,
             http.HTTPStatusCode.UNAUTHORIZED,
             http.HTTPStatusCode.FORBIDDEN,
             http.HTTPStatusCode.NOT_FOUND,
             http.HTTPStatusCode.GONE,
             http.HTTPStatusCode.UNAVAILABLE_FOR_LEGAL_REASONS,
             }
    """
    HTTP Response status codes that indicate an issue with the request that
    prevents deterministically deciding whether the requested resource is
    available.
    """
    Unknown = {http.HTTPStatusCode.INTERNAL_SERVER_ERROR,
               http.HTTPStatusCode.BAD_GATEWAY,
               http.HTTPStatusCode.SERVICE_UNAVAILABLE,
               http.HTTPStatusCode.GATEWAY_TIMEOUT,
               }

    def __init__(self, analyser: str,
                 http_acquirer: Optional[http.HTMLAcquirer] = None):
        super().__init__(analyser=analyser)
        self._http = http_acquirer or http.HTMLAcquirer()

    def get_url(self, url: str) -> http.Response:
        """
        Downloads the contents of `url` and returns the raw HTTP response.
        Appropriate HTTP Redirects, which would be respected by the user's
        browser, are also transparently respected by this method.
        """
        return self._http.get_url(url)

    def get_dom(self, url: str) -> Optional[html.HtmlElement]:
        """
        Downloads the content of `url`.
        If the download is successful, parses the obtained HTML and returns the
        parsed `ElementTree` corresponding to its DOM.
        """
        return self._http.get_dom(url)

    def check_response(self, response: http.Response) -> Ternary:
        """
        Selects whether the HTTP status code in the `response` object is
        indicating an "OK" (page is there), a "NOT OK" (page is
        deterministically not there), or that it could not be determined.
        """
        status = response.status
        if status in self.Ok:  # Deterministically clear.
            return True
        if status in self.NotOk:  # Deterministically failed.
            return False
        if status in self.Unknown:  # Unknown result, could not determine.
            return None

        error("Received unhandled HTTP status '%d %s'!",
              status, response.reason)
        return None

    def skip(self, _checker: str, url: str) -> Status:
        return Status.MISSING if not url else Status.OK

    ResponseToVerifyStatus = {True: Status.OK,
                              False: Status.NOT_OK,
                              None: Status.UNKNOWN
                              }

    def verify(self, checker: str, url: str) -> Outcome:
        """
        Verifies that the given URL is openable as an HTTP request and returns
        a "truthy" HTTP response code.

        Notes
        -----
        The contents of the page is not analysed.
        """
        try:
            trace("%s/%s -> %s ...", self.analyser, checker, url)
            response = self.get_url(url)
        except urllib3.exceptions.HTTPError:
            import traceback
            traceback.print_exc()

            return Status.UNKNOWN, None

        http_status = self.check_response(response)
        return self.ResponseToVerifyStatus[http_status], response


class HTMLAnchorVerifier(HTTPStatusCodeVerifier):
    """
    Generic URL verifier that checks whether the URL returns a valid HTTP
    status code that indicates the URL resolves to a documentation that is
    accessible by the user, and that the anchor in the ``GET`` response's DOM
    exists.
    This is used for documentation pages where several entries are on the same
    page.

    Notes
    -----
    This class caches the response for the same base URL (excluding anchors)
    to speed up queries.
    """

    kind = "webpage#anchor"

    def __init__(self, analyser: str,
                 cache_size=http.CachingHTMLAcquirer.DefaultCacheSize):
        super().__init__(analyser=analyser,
                         http_acquirer=http.CachingHTMLAcquirer(cache_size))

    def verify(self, checker: str, url: str) -> Outcome:
        """
        Executes the verification for `checker` of the site of the given
        `url`.
        In addition to downloading the `url` contents and checking the HTTP
        status code, check if the anchor, as specified by the `url`, exists
        appropriately (a real browser would have found the anchor to jump to).
        If the `url` does not contain an anchor, provides the same behaviour,
        except for internal caching, as `HTTPStatusCodeVerifier.verify()`
        would.
        """
        page, anchor = self._http.split_anchor(url)
        try:
            trace("%s/%s -> %s ...", self.analyser, checker, url)
            response = self.get_url(page)
        except lxml.etree.LxmlError:  # pylint: disable=c-extension-no-member
            import traceback
            traceback.print_exc()

            return Status.UNKNOWN, None
        except urllib3.exceptions.HTTPError:
            return Status.UNKNOWN, None

        http_status = self.check_response(response)
        if not anchor or not http_status:
            return self.ResponseToVerifyStatus[http_status], response

        dom = self.get_dom(page)
        if dom is None:
            return Status.NOT_OK, response
        dom = cast(html.HtmlElement, dom)  # mypy does not recognise the if.

        if dom.find(f".//*[@id=\"{anchor}\"]") is not None:
            return Status.OK, response
        if "github.com" in url and ".md#" in url:
            # GitHub is doing something nasty with how they render Markdown.
            #
            # If you have a ToC and a header, they will generate two
            #     <a href="#my-header" ...>
            # tags, from which the invisible "permalink button" one near the
            # actual header will have the
            #     id="user-content-my-header"
            # attribute as well.
            #
            # Specifying "whatever.md#my-header" will scroll the viewport to
            # the heading, even though the previous XPath query won't return
            # a valid element.
            # This is because they use a custom web frontend to render the
            # code from an embedded JavaScript object, so the render itself
            # is not part of the downloaded DOM unless executed by a browser.
            if anchor in response.data.decode():
                return Status.OK, response

        return Status.NOT_OK, response

    def find_anchors_for_text(self, url: str, text: str) -> Iterable[str]:
        """
        Find elements in the DOM for `url` that contain the text `text` and
        return the closest ancestors that have an ``id`` attribute that the
        user can jump to.
        """
        page, _ = self._http.split_anchor(url)
        dom = self.get_dom(page)
        if dom is None:
            return iter(())
        dom = cast(html.HtmlElement, dom)

        return map(lambda e: e.attrib["id"], dom.xpath(
            f"//*[contains(text(), \"{text}\")]/ancestor::*[@id][1]"))
