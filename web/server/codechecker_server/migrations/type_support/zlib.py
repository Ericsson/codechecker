# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Suppoting methods for the migration from raw BLOBs that actually contain ZLib
data to the ZLibCompressed* decorated types.
"""
from typing import Tuple
import zlib

from codechecker_server.database.types import zlib as db_zlib


_default_zlib_type = db_zlib.ZLibCompressedBlob()


def upgrade_zlib_raw_to_tagged(
    value: bytes,
    zlib_type: db_zlib.ZLibCompressedBlob = _default_zlib_type
) -> bytes:
    """
    Recompresses the given raw ZLib-compressed ``value`` by tagging it with the
    ``kind`` appropriate for the given ``zlib_type`` ``ZLibCompressed`` type
    decorator.

    This method is costly as it searches for the exact compression level that
    was originally used by performing up to 12 rounds of re-encoding
    internally until the right compression level is figured out.
    Unfortunately, there are no good and deterministic ways to recover this
    information in a single go by observing an already compressed buffer.

    The exact compression level might not be found, e.g., if the zlib version
    used to encode the original 'value' no longer matches what is available
    on the current machine, and all possible compression levels produce a
    different result than what was originally present. In this case,
    ``zlib.Z_BEST_COMPRESSION`` will be used for the re-compressed buffer.
    """
    buffer = zlib.decompress(value)

    def _compress_attempt(level: int) -> Tuple[bool, bytes]:
        compressed = zlib.compress(buffer, level)
        return (compressed == value, compressed)

    for compression_level in reversed(range(zlib.Z_DEFAULT_COMPRESSION,
                                            zlib.Z_BEST_COMPRESSION + 1)):
        success, compressed = _compress_attempt(compression_level)
        if success:
            return zlib_type._encode(compressed)
    else:
        return zlib_type._encode(zlib.compress(buffer,
                                               zlib.Z_BEST_COMPRESSION))


def downgrade_zlib_tagged_to_raw(value: bytes) -> bytes:
    """
    Untags the type adaptor header from ``value``, extracting the still
    compressed payload from it.

    The downgrade process purposefully does not use the routines that would
    validate the ``kind`` of the tagged buffer, as that metadata is only
    useful for the type decorator and does not affect payload representation.

    This method is cheap, as during decompression, the compression_level
    is not relevant information for the algorithm itself. There might be
    performance pros and cons when comparing different compression levels,
    but the discussion and the evidence for such is inconclusive.
    """
    payload_start, _, _ = _default_zlib_type._parse_tag(value)
    return value[payload_start:]
