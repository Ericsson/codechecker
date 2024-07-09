# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Provides I/O with the configuration files that describe checker labels."""
from collections import deque
from enum import Enum, auto as Enumerator
import json
import pathlib
from typing import Callable, Dict, List, Optional, Set, cast

from codechecker_common.checker_labels import split_label_kv

from .output import Settings as OutputSettings, error, trace
from . import fixit


# The raw label structure, as present verbatim in the configuration file.
# (e.g., {"bugprone-foo": ["severity:HIGH", "profile:default"]})
_ConfigFileLabels = Dict[str, List[str]]


# Maps: checker -> single label value | None
# (e.g., {"bugprone-foo": "HIGH"})
SingleLabels = Dict[str, Optional[str]]

# Maps the label keys into a list of label values with that key.
# (e.g., {"profile": ["default"], "severity": ["HIGH"]})
KeySplitLabels = Dict[str, List[str]]

# Maps: checker -> [label key -> label values...]...
# (e.g., {"bugprone-foo": {"profile": ["default", "sensitive", "extreme"]}}
MultipleLabels = Dict[str, KeySplitLabels]


K_Labels = "labels"  # pylint: disable=invalid-name
K_LabelToolSkipDirective = "label-tool-skip"  # pylint: disable=invalid-name


class SkipDirectiveRespectStyle(Enum):
    """
    Do not respect the directive.
    """
    NO_ACTION = Enumerator()

    """
    Fetch the list of the relevant skip directives automatically, and respect
    it.
    """
    AUTOMATIC_YES = Enumerator()

    """
    Respect only the skip list passed directly with the style argument, and
    do not perform automatic fetching.
    """
    AS_PASSED = Enumerator()


def _load_json(path: pathlib.Path) -> Dict:
    try:
        with path.open("r") as file:
            return json.load(file)
    except OSError:
        import traceback
        traceback.print_exc()

        error("Failed to open label config file '%s'", path)
        raise
    except json.JSONDecodeError:
        import traceback
        traceback.print_exc()

        error("Failed to parse label config file '%s'", path)
        raise


def _save_json(path: pathlib.Path, data: Dict):
    try:
        with path.open("w") as file:
            json.dump(data, file, indent=2, sort_keys=True)
            file.write('\n')
    except OSError:
        import traceback
        traceback.print_exc()

        error("Failed to write label config file '%s'", path)
        raise
    except (TypeError, ValueError):
        import traceback
        traceback.print_exc()

        error("Failed to encode label config file '%s'", path)
        raise


def _project_labels_by_key(
    label_cfg: _ConfigFileLabels,
    key: str,
    value_predicate: Optional[Callable[[str], bool]] = None
) -> _ConfigFileLabels:
    """
    Projects the `label_cfg` to a mapping of ``Checker -> List[T]``, in which
    only the **values** of labels with the specified `key` are kept, and all
    other labels are ignored.

    If `value_predicate` is set, in addition to the `key` matching, will only
    keep values that satisfy the given predicate.
    """
    return {
        checker: [label_v
                  for label in labels
                  for label_k, label_v in (split_label_kv(label),)
                  if label_k == key
                  and (not value_predicate or value_predicate(label_v))]
        for checker, labels in label_cfg.items()}


class MultipleLabelsError(Exception):
    """
    Raised by `get_checker_labels` if multiple labels exist for the same key.
    """

    def __init__(self, key):
        super().__init__(f"Multiple labels with key: {key}")
        self.key = key


def get_checkers_with_ignore_of_key(path: pathlib.Path,
                                    key: str) -> Set[str]:
    """
    Loads the checker config label file available at `path` and filters it for
    the list of checkers that are set to ignore/skip labels of the specified
    `key`, i.e., a ``label-tool-skip:KEY`` exists for `key`'s value amongst the
    checker's labels.
    """
    try:
        label_cfg = cast(_ConfigFileLabels, _load_json(path)[K_Labels])
    except KeyError:
        error("'%s' is not a label config file", path)
        raise

    labels_skip_of_key = _project_labels_by_key(
        label_cfg, K_LabelToolSkipDirective,
        lambda skip: skip == key)
    return {checker
            for checker, labels in labels_skip_of_key.items()
            if len(labels)}


def get_checker_labels(
    analyser: str,
    path: pathlib.Path,
    key: str,
    skip_directive_handling: SkipDirectiveRespectStyle =
    SkipDirectiveRespectStyle.AUTOMATIC_YES,
    checkers_to_skip: Optional[Set[str]] = None
) -> SingleLabels:
    """
    Loads and filters the checker config label file available at `path`
    for the `key` label. Raises `MultipleLabelsError` if there is at least
    two labels with the same `key`.

    Labels of a particular "type" for which a skip directive
    (``label-tool-skip:KEY``, e.g., ``label-tool-skip:severity``) exists will
    not appear, as-if the label did not even exist, depending on
    `skip_directive_handling`'s value.
    """
    try:
        label_cfg = cast(_ConfigFileLabels, _load_json(path)[K_Labels])
    except KeyError:
        error("'%s' is not a label config file", path)
        raise

    if skip_directive_handling == SkipDirectiveRespectStyle.NO_ACTION or \
            checkers_to_skip is None:
        checkers_to_skip = set()
    elif skip_directive_handling == SkipDirectiveRespectStyle.AUTOMATIC_YES:
        checkers_to_skip = get_checkers_with_ignore_of_key(path, key)
    filtered_labels = {
        checker: labels
        for checker, labels in _project_labels_by_key(label_cfg, key).items()
        if checker not in checkers_to_skip}
    if OutputSettings.trace():
        deque((trace("No '%s:' label found for '%s/%s'",
                     key, analyser, checker)
               for checker, labels in filtered_labels.items()
               if not labels and checker not in checkers_to_skip), maxlen=0)

    if any(len(labels) > 1 for labels in filtered_labels.values() if labels):
        raise MultipleLabelsError(key)

    return {checker: labels[0] if labels else None
            for checker, labels in filtered_labels.items()}


def get_checker_labels_multiple(path: pathlib.Path) -> MultipleLabels:
    """
    Loads the checker config label file available at `path` and transfors it
    into a `MultipleLabels` structure, and returns it.

    This method **DOES NOT** respect the ``label-tool-skip`` directives.
    """
    try:
        label_cfg = cast(_ConfigFileLabels, _load_json(path)[K_Labels])
    except KeyError:
        error("'%s' is not a label config file", path)
        raise

    return {
        checker: {
            key: [label_v2
                  for label_kv2 in labels
                  for label_k2, label_v2 in (split_label_kv(label_kv2),)
                  if label_k2 == key
                  ]
            for label_kv in labels
            for key, _ in (split_label_kv(label_kv),)
        }
        for checker, labels in label_cfg.items()
    }


def apply_label_fixes(labels: MultipleLabels,
                      fixes: fixit.FixMap) -> MultipleLabels:
    """
    Applies the `FixAction`s in `fixes` to the `labels` structure, in place.
    (Returns a reference to the input `labels` parameter.)

    The `fixes` are applied in the order they appear in the input.
    Consistency and order-independence of the resulting actions are **NOT**
    verified by this function, please see `fixit.filter_conflicting_fixes`
    for that.
    """
    for checker, fix_actions in fixes.items():
        checker_labels: KeySplitLabels = labels.get(checker, {})

        for fix in fix_actions:
            if isinstance(fix, (fixit.ModifyLabelAction,
                                fixit.RemoveLabelAction)):
                ok, ov = split_label_kv(cast(str, fix.old))
                checker_labels[ok] = [
                    v_ for v_ in checker_labels.get(ok, []) if v_ != ov]

            if isinstance(fix, (fixit.AddLabelAction,
                                fixit.ModifyLabelAction)):
                nk, nv = split_label_kv(cast(str, fix.new))
                checker_labels[nk] = checker_labels.get(nk, []) + [nv]

        labels[checker] = checker_labels

    return labels


def update_checker_labels(
    analyser: str,
    path: pathlib.Path,
    key: str,
    updates: SingleLabels,
    skip_directive_handling: SkipDirectiveRespectStyle =
    SkipDirectiveRespectStyle.AUTOMATIC_YES,
    checkers_to_skip: Optional[Set[str]] = None
):
    """
    Loads a checker config label file available at `path` and updates the
    `key` labels based on the `updates` structure, overwriting or adding the
    existing label (or raising `MultipleLabelsError` if it is not unique which
    one to overwrite), then writes the resulting data structure back to `path`.

    Labels of a particular "type" for which a skip directive
    (``label-tool-skip:KEY``, e.g., ``label-tool-skip:severity``) exists will
    not be written or updated in the config file, even if the value was present
    in `updates`, depending on `skip_directive_handling`'s value.
    """
    try:
        config = _load_json(path)
        label_cfg = cast(_ConfigFileLabels, config[K_Labels])
    except KeyError:
        error("'%s's '%s' is not a label config file", analyser, path)
        raise

    if skip_directive_handling == SkipDirectiveRespectStyle.NO_ACTION or \
            checkers_to_skip is None:
        checkers_to_skip = set()
    elif skip_directive_handling == SkipDirectiveRespectStyle.AUTOMATIC_YES:
        checkers_to_skip = get_checkers_with_ignore_of_key(path, key)
    label_indices = {
        checker: [index for index, label in enumerate(labels)
                  if split_label_kv(label)[0] == key]
        for checker, labels in label_cfg.items()
        if checker not in checkers_to_skip}

    if any(len(indices) > 1 for indices in label_indices.values()):
        raise MultipleLabelsError(key)
    label_indices = {checker: indices[0] if len(indices) == 1 else None
                     for checker, indices in label_indices.items()}
    for checker, new_label in updates.items():
        if checker in checkers_to_skip:
            continue

        try:
            checker_labels = label_cfg[checker]
        except KeyError:
            label_cfg[checker] = []
            label_indices[checker] = None

            checker_labels = label_cfg[checker]

        idx = label_indices[checker]
        e = f"{key}:{new_label}"
        if idx is not None:
            checker_labels[idx] = e
        else:
            checker_labels.insert(0, e)
            label_cfg[checker] = sorted(checker_labels)

    _save_json(path, config)


def update_checker_labels_multiple_overwrite(
    analyser: str,
    path: pathlib.Path,
    labels: MultipleLabels
):
    """
    Loads the checker config label file available at `path` and updates it to
    reflect the **CONTENTS** of `labels`.
    Entries in the file which do not have a corresponding key in `labels` are
    left intact, but the labels for which **ANY** value exists in `labels` are
    **OVERWRITTEN** as a single entity.
    To mark a checker for **DELETION**, map it in `labels` to an explicit
    `None`.

    This method **DOES NOT** respect the ``label-tool-skip`` directives.
    """
    try:
        config = _load_json(path)
        label_cfg = cast(_ConfigFileLabels, config[K_Labels])
    except KeyError:
        error("'%s's '%s' is not a label config file", analyser, path)
        raise

    for checker, kvs in labels.items():
        if kvs is None:
            try:
                del label_cfg[checker]
            except KeyError:
                pass
            continue

        label_cfg[checker] = sorted({f"{k}:{v}"
                                     for k, vs in kvs.items()
                                     for v in vs
                                     })

    _save_json(path, config)
