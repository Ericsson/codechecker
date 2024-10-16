# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Provides I/O with the configuration files that describe checker labels."""
from collections import deque
import json
import pathlib
from typing import Dict, List, Optional, cast

from codechecker_common.checker_labels import split_label_kv

from .output import Settings as OutputSettings, error, trace


_ConfigFileLabels = Dict[str, List[str]]

SingleLabels = Dict[str, Optional[str]]
Labels = Dict[str, Dict[str, str]]


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


class MultipleLabelsError(Exception):
    """
    Raised by `get_checker_labels` if multiple labels exist for the same key.
    """

    def __init__(self, key):
        super().__init__("Multiple labels with key: %s", key)
        self.key = key


def get_checker_labels(analyser: str, path: pathlib.Path, key: str) \
        -> SingleLabels:
    """
    Loads and filters the checker config label file available at `path`
    for the `key` label. Raises `MultipleLabelsError` if there is at least
    two labels with the same `key`.
    """
    try:
        label_cfg = cast(_ConfigFileLabels, _load_json(path)["labels"])
    except KeyError:
        error("'%s' is not a label config file", path)
        raise

    filtered_labels = {
        checker: [label_v
                  for label in labels
                  for label_k, label_v in (split_label_kv(label),)
                  if label_k == key]
        for checker, labels in label_cfg.items()}
    if OutputSettings.trace():
        deque((trace("No '%s:' label found for '%s/%s'",
                     key, analyser, checker)
               for checker, labels in filtered_labels.items()
               if not labels), maxlen=0)

    if any(len(labels) > 1 for labels in filtered_labels.values()):
        raise MultipleLabelsError(key)
    return {checker: labels[0] if labels else None
            for checker, labels in filtered_labels.items()}


def update_checker_labels(analyser: str,
                          path: pathlib.Path,
                          key: str,
                          updates: SingleLabels):
    """
    Loads a checker config label file available at `path` and updates the
    `key` labels based on the `updates` structure, overwriting or adding the
    existing label (or raising `MultipleLabelsError` if it is not unique which
    one to overwrite), then writes the resulting data structure back to `path`.
    """
    try:
        config = _load_json(path)
        label_cfg = cast(_ConfigFileLabels, config["labels"])
    except KeyError:
        error("'%s's '%s' is not a label config file", analyser, path)
        raise

    label_indices = {
        checker: [index for index, label in enumerate(labels)
                  if split_label_kv(label)[0] == key]
        for checker, labels in label_cfg.items()
    }

    if any(len(indices) > 1 for indices in label_indices.values()):
        raise MultipleLabelsError(key)
    label_indices = {checker: indices[0] if len(indices) == 1 else None
                     for checker, indices in label_indices.items()}
    for checker, new_label in updates.items():
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
