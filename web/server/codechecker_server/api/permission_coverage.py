# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Static enforcement that every Thrift API method on the report server has
some form of permission check.

This is a security boundary: a Thrift method that lacks any permission
check is reachable by any authenticated user, which would allow an
unprivileged user to invoke functionality reserved for product admins,
superusers, or even unauthenticated callers in principle.

The check is run from two places:

  * From a unit test, so that a PR that introduces an unprotected method
    fails CI before being merged.

  * From the server's start_server() function, so that even if such a PR
    were merged anyway, the server refuses to start instead of serving
    an exploitable endpoint.

The same logic is used in both, so they can never disagree.

A method is considered "protected" if any of the following hold:

  * It has the @requires_view decorator applied.
  * One of its first few statements calls into one of the existing
    self.__require_*() permission helpers (admin, access, store,
    permission, etc.).
  * It is listed in _DELEGATED_PROTECTION and the named delegate
    helper itself satisfies one of the above conditions.

The set of Thrift methods to check is read from the generated Thrift
Python module (codechecker_api.codeCheckerDBAccess_v6.codeCheckerDBAccess),
which is shipped with both development and deployed installations.
"""
import ast
import inspect
from pathlib import Path
from typing import List, Set

from codechecker_api.codeCheckerDBAccess_v6 import codeCheckerDBAccess


# Path to the handler implementing codeCheckerDBAccess_v6.
# Resolved relative to this file so it works in both source and built
# layouts.
_HANDLER_PATH = Path(__file__).parent / "report_server.py"

# Name of the Python class that implements the Thrift Iface.
_HANDLER_CLASS_NAME = "ThriftRequestHandler"

# Statement positions to inspect for an in-body permission check.
# Most methods place the check as their first non-docstring statement,
# but a handful do per-argument preprocessing first; three is a safe
# limit.
_MAX_PROLOGUE_STATEMENTS = 3

# Decorator names that count as a permission check on their own.
_PERMISSION_DECORATORS = frozenset({
    "requires_view",
})

# Substrings inside an attribute access that indicate a permission
# helper was called. We match on suffix rather than equality because
# Python's name-mangling rewrites `self.__require_view` to e.g.
# `self._ThriftRequestHandler__require_view` at parse time as well.
_PERMISSION_CHECK_SUFFIXES = (
    "_require_view",
    "__require_view",
    "__require_admin",
    "__require_access",
    "__require_store",
    "__require_permission",
    "__require_supermission",
    "__require_privilaged_access",
    "__require_permission_view",
)

# Thrift methods that delegate their permission check to a helper
# rather than performing it as one of their own first statements.
#
# Each entry maps the Thrift method name to the helper method it
# delegates to. The check below verifies that the named helper itself
# performs a permission check; if a future change removes that helper's
# check, the delegation entry will fail and the Thrift method will be
# reported as unprotected.
_DELEGATED_PROTECTION = {
    # Both massStoreRun variants share the same upload pipeline,
    # __massStoreRun_common, which calls self.__require_store() before
    # touching any data.
    "massStoreRun": "__massStoreRun_common",
    "massStoreRunAsynchronous": "__massStoreRun_common",
}


def _thrift_method_names() -> Set[str]:
    """Return the names of all methods on the Thrift service Iface."""
    iface = codeCheckerDBAccess.Iface
    return {
        name
        for name, _ in inspect.getmembers(iface, inspect.isfunction)
    }


def _is_permission_decorator(decorator_node: ast.expr) -> bool:
    """Return True if the AST decorator node names a known permission
    decorator."""
    if isinstance(decorator_node, ast.Name):
        return decorator_node.id in _PERMISSION_DECORATORS
    if isinstance(decorator_node, ast.Attribute):
        return decorator_node.attr in _PERMISSION_DECORATORS
    return False


def _statement_is_permission_check(stmt: ast.stmt) -> bool:
    """Return True if the statement is a self.__require_*()-style
    call."""
    if not isinstance(stmt, ast.Expr):
        return False
    if not isinstance(stmt.value, ast.Call):
        return False
    func = stmt.value.func
    if not isinstance(func, ast.Attribute):
        return False
    return any(func.attr.endswith(suffix)
               for suffix in _PERMISSION_CHECK_SUFFIXES)


def _method_is_protected(method_node: ast.FunctionDef) -> bool:
    """Return True if the method has either a permission decorator or
    a permission-check call in its first few statements."""
    for decorator in method_node.decorator_list:
        if _is_permission_decorator(decorator):
            return True
    # Skip a leading docstring, then look at the next few statements.
    body = method_node.body
    if body and isinstance(body[0], ast.Expr) \
            and isinstance(body[0].value, ast.Constant) \
            and isinstance(body[0].value.value, str):
        body = body[1:]
    for stmt in body[:_MAX_PROLOGUE_STATEMENTS]:
        if _statement_is_permission_check(stmt):
            return True
    return False


def _build_method_index(class_node: ast.ClassDef) -> dict:
    """Map method name -> FunctionDef node for a class."""
    return {
        m.name: m
        for m in class_node.body
        if isinstance(m, ast.FunctionDef)
    }


def find_unprotected_methods() -> List[str]:
    """Return a list of Thrift method names on ThriftRequestHandler
    that have no detectable permission check. Empty list means
    everything is protected."""
    thrift_methods = _thrift_method_names()
    tree = ast.parse(_HANDLER_PATH.read_text(encoding="utf-8"))

    unprotected: List[str] = []
    for cls in ast.walk(tree):
        if not isinstance(cls, ast.ClassDef):
            continue
        if cls.name != _HANDLER_CLASS_NAME:
            continue

        methods_by_name = _build_method_index(cls)

        for member in cls.body:
            if not isinstance(member, ast.FunctionDef):
                continue
            if member.name not in thrift_methods:
                continue

            if _method_is_protected(member):
                continue

            # Not directly protected; consult the delegation map.
            delegate_name = _DELEGATED_PROTECTION.get(member.name)
            if delegate_name is not None:
                # Look up the delegate by its mangled name as it would
                # appear inside the same class (double-underscore
                # methods are name-mangled).
                mangled = f"_{_HANDLER_CLASS_NAME}{delegate_name}"
                delegate_node = (
                    methods_by_name.get(delegate_name)
                    or methods_by_name.get(mangled))
                if delegate_node is not None \
                        and _method_is_protected(delegate_node):
                    continue
                # Delegation declared but delegate missing or itself
                # unprotected -- fall through, this method is
                # unprotected.

            unprotected.append(member.name)

    return sorted(unprotected)


def assert_all_thrift_methods_protected() -> None:
    """Raise RuntimeError listing any Thrift methods that are not
    permission-protected. Called from both the unit test and from
    start_server() at server startup."""
    unprotected = find_unprotected_methods()
    if unprotected:
        raise RuntimeError(
            "Thrift API methods without a detectable permission check "
            "were found. Add either an @requires_view decorator, an "
            "in-body self.__require_*() call, or a "
            "_DELEGATED_PROTECTION entry for each:\n  "
            + "\n  ".join(unprotected))
