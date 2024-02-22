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
from typing import Any, Callable, Optional
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

    The ``value`` is first decompressed using the native ``zlib`` library,
    and then recompressed according to the ``compression_level`` of the
    ``zlib_type``. Then, the type-appropriate value prefix is prepended.
    """
    buffer = zlib.decompress(value)
    recompressed = zlib.compress(buffer, zlib_type.compression_level)
    return zlib_type._encode(recompressed)


def upgrade_zlib_serialised(
    value: bytes,
    zlib_type: db_zlib.ZLibCompressedSerialisable,
    original_deserialisation_fn: Optional[
        Callable[[Optional[str]], Optional[Any]]] = None
) -> bytes:
    """
    Reserialises and recompreesses the given raw ZLib-compressed ``value`` to
    the serialised version stipulated by ``zlib_type``.

    The ``value`` is first deserialised (after decompression) by
    ``original_deserialisation_fn`` (or, if unset, the appropraite
    deserialisation function of ``zlib_type``) to a pure object. Following,
    it is serialised and stored through the type adaptor.

    This function uses whichever ``compression_level`` the ``zlib_type`` was
    instantiated with.
    """
    deserialise = original_deserialisation_fn or zlib_type.deserialise

    def decompress_and_deserialise(compressed_buffer: bytes) -> Optional[Any]:
        buffer = zlib.decompress(compressed_buffer)
        serialised = buffer.decode(errors="strict")
        return deserialise(serialised)

    data_object = decompress_and_deserialise(value)
    return zlib_type.process_bind_param(data_object, "")


def downgrade_zlib_tagged_to_raw(value: bytes) -> bytes:
    """
    Untags the type adaptor header from ``value``, extracting the still
    compressed payload from it.

    The downgrade process purposefully does not use the routines that would
    validate the ``kind`` of the tagged buffer, as that metadata is only
    useful for the type decorator and does not affect payload representation.
    """
    payload_start, _, _ = _default_zlib_type._parse_tag(value)
    return value[payload_start:]


def downgrade_zlib_serialised(
    value: bytes,
    zlib_type: db_zlib.ZLibCompressedSerialisable,
    original_serialisation_fn: Optional[
        Callable[[Optional[Any]], Optional[str]]] = None,
    compression_level=zlib.Z_BEST_COMPRESSION
) -> Optional[bytes]:
    """
    Reserialises and recompresses the given tagged ZLib-compressed ``value``
    to a serialised and raw-encoded version stipulated by ``zlib_type``.

    The ``value`` is first deserialised (after decompression) through the
    type adaptor to a pure object. Following, it is serialised by
    ``original_serialisation_fn`` (or, if unset, the appropriate serialisation
    function of ``zlib_type``) to a string representation, which is then
    compressed by the native ``zlib`` library, using the specified
    ``compression_level``.
    """
    serialise = original_serialisation_fn or zlib_type.serialise

    def serialise_and_compress(o: Any) -> Optional[bytes]:
        serialised = serialise(o)
        if not serialised:
            return None
        buffer = serialised.encode(errors="strict")
        return zlib.compress(buffer, compression_level)

    data_object = zlib_type.process_result_value(value, "")
    return serialise_and_compress(data_object)
