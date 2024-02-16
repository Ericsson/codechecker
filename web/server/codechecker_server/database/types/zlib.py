# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Implements sqlalchemy.types.TypeDecorator to automatically and transparently
load and store textual data with zlib-compression.
"""
import json
import re
from typing import Any, Callable, Optional, Tuple, cast
import zlib

from sqlalchemy.types import LargeBinary, TypeDecorator


TagRegex = re.compile(r"^(.+)\[(.+),(-?\d+)\]$")


class ZLibCompressedBlob(TypeDecorator):
    """Arbitrary user-defined binary data compressed with ZLib."""
    impl = LargeBinary
    client_type = bytes

    def __init__(self, compression_level=zlib.Z_BEST_COMPRESSION,
                 kind="blob"):
        """
        Defines an instantiation of the decorator that converts binary data
        into ZLib-compressed representation.

        The ``compression_level`` is a parameter that only directly influences
        the characteristics during compression. Irrespective of the
        ``compression_level`` used, any ZLib-compressed data can be
        successfully decompressed - this value is not "validated" during
        decompression.

        There are conflicting opinions and measurements as to whether a
        higher compression level will result in slower or faster decompression
        when compared with a lower compression level.

        The ``kind`` parameter is used as a tag to indicate what type of
        object is stored in the database. This value is serialised directly
        into the uncompressed header of the database row, and is validated
        during reading. This value should not be domain-specific (e.g.,
        "report-metadata"), but only indicative of the underlying
        "file format" that is compressed (e.g., "string" or "json").
        """
        super().__init__()
        self.compression_level = compression_level
        self.kind = kind

    def process_bind_param(self, value: Optional[client_type], dialect: str) \
            -> Optional[impl]:
        """
        Transforms the bound parameter of the client-side database query to
        the value of the underyling database-side implementation type.
        That is, performs the conversion Python -> DB.
        """
        return cast(LargeBinary, self._encode(self._compress(value))) \
            if value is not None else None

    def process_result_value(self, value: Optional[impl], dialect: str) \
            -> Optional[client_type]:
        """
        Transforms a value obtained from the underlying implementation
        (database-side) type to the value and type expected by the client-side
        code.
        That is, performs the conversion DB -> Python.
        """
        return self._decompress(self._decode(value)) \
            if value is not None else None

    def _make_tag(self) -> bytes:
        """
        Creates the tag prefix that is added to the user-defined data.
        This is primarily done to explicitly indicate for server operators
        that the otherwise seemingly arbitrary information in the database
        should actually be understood as a ZLib-compressed payload.
        """
        if '@' in self.kind:
            raise ValueError("'kind' must not contain '@', as this character "
                             "is reserved for the tagging format")
        return ("zlib[%s,%d]@" % (self.kind, self.compression_level)).encode()

    def _parse_tag(self, buffer: bytes) -> Tuple[int, str, int]:
        """
        Parses the tagging header of a ZLib-compressed payload created by
        ``_encode()``.

        The returned value is a tuple in the following order:

            1. The index where the compressed payload begins.
            2. The ``kind`` value that was encoded in the header.
            3. The ``compression_level`` that was encoded in the header.
        """
        split_index = buffer.index('@'.encode())
        header = buffer[:split_index].decode()
        match = TagRegex.match(header)
        if not match:
            raise ValueError("'%s' is not a valid ZLib tag", header)

        algorithm, kind, level = match.groups()
        if algorithm != "zlib":
            raise ValueError("'%s' is not a valid ZLib tag, unexpected "
                             "algorithm '%s'", header, algorithm)
        level = int(level)

        return (split_index + 1, kind, level)

    def _compress(self, value: bytes) -> bytes:
        """
        Compresses the input payload ``value`` with the class's
        ``compression_level``.
        """
        return zlib.compress(value, self.compression_level)

    def _decompress(self, buffer: bytes) -> bytes:
        """
        Uncompresses the headerless payload into its raw, original value.
        """
        return zlib.decompress(buffer)

    def _encode(self, value: bytes) -> bytes:
        """Formats the input payload ``value`` to a tagged representation."""
        return self._make_tag() + value

    def _decode(self, buffer: bytes) -> bytes:
        """
        Decodes the tagged ZLib-compressed ``buffer`` if it is the ``kind``
        that is expected by the current instance.
        Returns the original payload.
        """
        payload_start, kind, _ = self._parse_tag(buffer)
        if kind != self.kind:
            raise ValueError("ZLib-compressed value of kind '%s' decoded "
                             "when expecting kind '%s' instead",
                             kind, self.kind)

        payload = buffer[payload_start:]
        return payload


class ZLibCompressedString(ZLibCompressedBlob):
    """
    Arbitrary user-defined textual data encoded and compressed with ZLib.
    """
    impl = ZLibCompressedBlob.impl
    client_type = str

    def __init__(self, compression_level=zlib.Z_BEST_COMPRESSION,
                 kind="text"):
        super().__init__(compression_level=compression_level, kind=kind)

    def process_bind_param(self, value: Optional[client_type], dialect: str) \
            -> Optional[impl]:
        if value is None:
            return None

        blob = value.encode(errors="ignore")
        return super().process_bind_param(blob, dialect)

    def process_result_value(self, value: Optional[impl], dialect: str) \
            -> Optional[client_type]:
        blob = super().process_result_value(value, dialect)
        if blob is None:
            return None

        return blob.decode(errors="ignore")


class ZLibCompressedSerialisable(ZLibCompressedString):
    """
    Allows creating types where arbitrary, user-defined data of a known
    serialisable format is serialised to string and then stored as an encoded,
    compressed ZLib binary value.
    """
    impl = ZLibCompressedString.impl
    client_type = Any

    def __init__(self, kind: str,
                 serialise_fn: Callable[[Optional[client_type]],
                                        Optional[str]],
                 deserialise_fn: Callable[[Optional[str]],
                                          Optional[client_type]],
                 compression_level=zlib.Z_BEST_COMPRESSION):
        super().__init__(compression_level=compression_level, kind=kind)
        self.serialise = serialise_fn
        self.deserialise = deserialise_fn

    def process_bind_param(self, value: Optional[client_type], dialect: str) \
            -> Optional[impl]:
        serialised = self.serialise(value)
        return super().process_bind_param(serialised, dialect)

    def process_result_value(self, value: Optional[impl], dialect: str) \
            -> Optional[client_type]:
        serialised = super().process_result_value(value, dialect)
        return self.deserialise(serialised)


class ZLibCompressedJSON(ZLibCompressedSerialisable):
    """
    Automatically encodes an arbitrary but JSON-serialisable object
    (scalar, ``list``, ``dict``) to the database, and stores it as a
    ZLib-compressed binary value.
    """

    @staticmethod
    def _json_to_str(o: Optional[Any]) -> str:
        # Use the most compact representation possible (according to the
        # json package docs), the data will be compressed anyway.
        return json.dumps(o,
                          indent=None,
                          separators=(',', ':'),
                          sort_keys=True
                          )

    @staticmethod
    def _str_to_json(s: Optional[str]) -> Optional[Any]:
        return json.loads(s) if s is not None else None

    def __init__(self, compression_level=zlib.Z_BEST_COMPRESSION):
        super().__init__(kind="json",
                         serialise_fn=ZLibCompressedJSON._json_to_str,
                         deserialise_fn=ZLibCompressedJSON._str_to_json,
                         compression_level=compression_level)
