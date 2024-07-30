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


_ConfigFileLabels = Dict[str, List[str]]

SingleLabels = Dict[str, Optional[str]]
Labels = Dict[str, Dict[str, str]]


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
        label_cfg = cast(_ConfigFileLabels, _load_json(path)["labels"])
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
        label_cfg = cast(_ConfigFileLabels, _load_json(path)["labels"])
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
        label_cfg = cast(_ConfigFileLabels, config["labels"])
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
