# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Handles the retrieval and access to a configuration structure loaded from
a file.
"""
from copy import deepcopy
from functools import partial
from enum import Enum, auto as Enumerator
from pathlib import Path, PosixPath, PurePosixPath
from typing import cast, Any, Callable, Dict, List, Optional, Tuple, Type, \
    Union

from .logger import get_logger
from .util import load_json


LOG = get_logger("system")

_K_CONFIGURATION = "__configuration"
_K_DATA_SLICE = "__data_slice"
_K_FILE_PATH = "__file_path"
_K_OPTION = "__option"
_K_OPTIONS = "__options"
_K_REF = "__ref"
_K_SCHEMA = "__schema"

OptionDict = Dict[str, "OptionBase"]


class AccessError(Exception):
    pass


class BackingDataError(AccessError):
    def __init__(self, option: "OptionBase", cfg: "Configuration"):
        super().__init__(
            f"'{option._basename}' ('{option._path}') not found in "
            f"configuration file '{cfg._file_path}'")


class BackingDataIndexError(AccessError, IndexError):
    def __init__(self, option: "OptionBase", cfg: "Configuration",
                 index: int, count: int):
        super().__init__(
            f"list index {index} out of range for '{option._basename}' "
            f"('{option._path}'), only {count} elements exist in "
            f"configuration file '{cfg._file_path}'")


def _get_children_options(parent_path: str, options: OptionDict) \
        -> OptionDict:
    if not parent_path.endswith('/'):
        parent_path = parent_path + '/'
    keys = set(map(lambda p: p[len(parent_path):].split('/', maxsplit=1)[0],
                   filter(lambda p: p.startswith(parent_path), options)))
    opts = [options[parent_path + k] for k in keys if k != '']
    children = {o._basename: o for o in opts}
    return children


def _step_into_child(option: "OptionBase", name: str):
    try:
        child_option = option._get_children()[name]
    except KeyError:
        # pylint: disable=raise-missing-from
        raise AttributeError(
            f"'{option._path}' option has no attribute '{name}'")

    try:
        access = getattr(child_option, "_access")
        return access
    except AttributeError:
        # pylint: disable=raise-missing-from
        raise AttributeError(
            f"'{child_option._path}' option can not be accessed")


class OptionBase:
    def __init__(self,
                 schema: "Schema",
                 name: Optional[str],
                 path: str,
                 description: Optional[str] = None):
        """
        Instantiates a new Option (base class) which designates, under a
        user-facing `name`, an element accessible in a configuration
        dictionary, as specified by `path`. ``/`` is the root of the
        configuration dictionary, and each "directory" is a named key in a
        sub-dictionary.

        The `Option` class hierarchy implement accessor classes, which deal
        with a type-safe and semantically correct reading of the specified
        values, but do not own or store the actual value of the option.
        An underlying storage object (almost certainly a `dict`) is always
        required during actual value access.

        For example, ``/max_run_count`` denotes the child of the top-level
        `dict`, whereas ``/keepalive/enabled`` is a child of a sub-tree.
        """
        self._schema_ = schema
        self._name_ = name
        self._description_ = description
        self._path_ = path

    @property
    def _name(self) -> str:
        return self._name_ if self._name_ is not None else f"<{self._path}>"

    @property
    def _description(self) -> Optional[str]:
        return self._description_

    @property
    def _path(self) -> str:
        return self._path_

    @property
    def _basename(self) -> str:
        return PurePosixPath(self._path).name

    def _get_children(self) -> OptionDict:
        """
        Returns the options that are registered as children of the current
        Option in the schema.
        """
        raise NotImplementedError(f"{str(type(self))} can not have children")

    class _Access:
        """
        The abstract base class to represent an ongoing access into a loaded
        `Configuration`, an established `Schema`.

        When using the member ``.`` (dot) operator on a `Configuration`,
        instances of this `_Access` class are created, allowing the client
        code to continue descending into potential inner attributes.

        This base class does nothing, apart from storing references to the
        core objects it was originally instantiated with.
        """

        def __init__(self, option: "OptionBase", cfg: "Configuration",
                     data_slice):
            # This code is frightening at first, but, unfortunately, the usual
            # 'self.member' syntax must be side-stepped such that
            # __getattr__ and __setattr__ can be implemented in a
            # user-friendly way.
            object.__setattr__(self, _K_OPTION, option)
            object.__setattr__(self, _K_CONFIGURATION, cfg)
            object.__setattr__(self, _K_DATA_SLICE, data_slice)

        def _get(self) -> Any:
            raise NotImplementedError(
                f"{str(type(object.__getattribute__(self, _K_OPTION)))} "
                "can not be get!")

        def _set(self, _value: Any) -> Any:
            raise NotImplementedError(
                f"{str(type(object.__getattribute__(self, _K_OPTION)))} "
                "can not be set!")

    def _access(self, _cfg: "Configuration", _data_slice: Dict[str, Any]) \
            -> Any:
        raise NotImplementedError(f"{str(type(self))} can not be accessed")


class OptionDirectory(OptionBase):
    """
    Represents a collection group of options, corresponding to the "directory"
    concept in filesystems. A directory may only contain sub-options and
    metadata, and has no value unto itself.
    """

    def __init__(self,
                 schema: "Schema",
                 name: Optional[str],
                 path: str,
                 description: Optional[str] = None):
        super().__init__(schema=schema, name=name, path=path,
                         description=description)

    def add_option(self, name: Optional[str], path: str, *args, **kwargs):
        """
        Adds an option with the given name and sub-path, relative to the
        current directory.

        See `Schema.add_option()` for details.
        """
        if not path.startswith("./"):
            raise ValueError("'path' must be relative to the OptionDirectory")

        # MyPy has a bug for this forwarding idiom, see
        # http://github.com/python/mypy/issues/6799.
        return self._schema_.add_option(name=name,
                                        path=path,
                                        parent=self,
                                        *args, **kwargs)  # type: ignore

    def _get_children(self) -> OptionDict:
        return _get_children_options(self._path, self._schema_.options)

    class _Access(OptionBase._Access):
        """
        Allows accessing, as attributes, the first-level children of
        "directories" (option groups).
        """

        def __init__(self, option: OptionBase, cfg: "Configuration",
                     data_slice: Dict[str, Any]):
            if option._basename != '':
                try:
                    data_slice = data_slice[option._basename]
                except KeyError:
                    data_slice[option._basename] = {}
                    data_slice = data_slice[option._basename]

            super().__init__(option=option, cfg=cfg, data_slice=data_slice)

        def __dir__(self):
            """
            Allows ``dir(...)`` to list the available children options' names.
            """
            return sorted(set(
                cast(List[Any], dir(super())) +
                cast(List[Any], list(self.__dict__.keys())) +
                cast(List[Any], list(object.__getattribute__(self, _K_OPTION)
                                     ._get_children().keys()))
            ))

        def __getattr__(self, name: str):
            """
            Continues the accessing descent of the `Configuration` using the
            object member access ``.`` (dot) operator.
            """
            opt, cfg, ds = \
                object.__getattribute__(self, _K_OPTION), \
                object.__getattribute__(self, _K_CONFIGURATION), \
                object.__getattribute__(self, _K_DATA_SLICE)
            access_ctor = _step_into_child(opt, name)
            return access_ctor(cfg, ds)._get()

        def __setattr__(self, name: str, value: Any):
            """
            Allows setting an attribute in the `Configuration` using the member
            access and set syntax of the ``.`` (dot) operator.

            ``X.foo = 5`` corresponds to ``X.__setattr__('foo', 5)``, and,
            thus, this method must be implemented here, for the
            `OptionDirectory`.
            """
            opt, cfg, ds = \
                object.__getattribute__(self, _K_OPTION), \
                object.__getattribute__(self, _K_CONFIGURATION), \
                object.__getattribute__(self, _K_DATA_SLICE)
            access_ctor = _step_into_child(opt, name)
            return access_ctor(cfg, ds)._set(value)

        def _get(self):
            """An access into a directory allows continuing to subelements."""
            return self

        def _set(self, _value: Any):
            option = object.__getattribute__(self, _K_OPTION)
            raise NotImplementedError(
                f"'{option._basename}' ('{option._path}') directory can not "
                "be set directly!")

    def _access(self, cfg: "Configuration", data_slice: Dict[str, Any]) \
            -> Any:
        return OptionDirectory._Access(self, cfg, data_slice)


class OptionDirectoryList(OptionDirectory):
    """
    Represents a special kind of OptionDirectory that acts as a "template" for
    inner ``Option``s.
    In a group, multiple copies of the same inner structure may exist, and
    each instance is accessible in practice by specifying a numeric index of
    the instance.

    Registered under the abstract path
    ``/authentication/method_ldap/authorities[]/``, this type takes care of
    requiring an index to access the children instances of this directory.
    """

    def __init__(self,
                 schema: "Schema",
                 name: Optional[str],
                 path: str,
                 description: Optional[str] = None):
        super().__init__(schema=schema, name=name, path=path,
                         description=description)

    @property
    def _basename(self) -> str:
        return PurePosixPath(self._path).name.replace("[]", '', 1)

    class _Access(OptionDirectory._Access):
        """
        Allows accessing, as if members of a list, the first-level children of
        "directories" (option groups).
        """
        def __init__(self, option: OptionBase, cfg: "Configuration",
                     data_slice: Dict[str, Any]):
            super().__init__(option=option, cfg=cfg, data_slice=data_slice)

        def __dir__(self):
            return sorted(set(
                cast(List[Any], dir(OptionBase._Access)) +
                cast(List[Any], list(self.__dict__.keys()))
            ))

        def __getattr__(self, _name: str):
            raise NotImplementedError("Accessing an array of schema elements "
                                      "must use the subscript operator []")

        def __setattr__(self, _name: str, _value: Any):
            raise NotImplementedError("Accessing an array of schema elements "
                                      "must use the subscript operator []")

        def __len__(self) -> int:
            """Returns the number of child elements in the option list."""
            return len(self._data_slice)

        def __getitem__(self, index: int):
            """
            Continues the accessing descent of the `Configuration` using the
            object indexing ``[]`` operator.
            """
            opt, cfg, ds = \
                object.__getattribute__(self, _K_OPTION), \
                object.__getattribute__(self, _K_CONFIGURATION), \
                object.__getattribute__(self, _K_DATA_SLICE)
            try:
                # Wrap the reference to the data of the single element into a
                # pseudo-directory structure that contains the data as-if
                # it was not the child of a list at all.
                elem_slice = {opt._basename: ds[index]}
            except IndexError:
                # pylint: disable=raise-missing-from
                raise BackingDataIndexError(opt, cfg, index, len(ds))

            # The indexed element of a directory list is a single directory.
            return OptionDirectory._Access(opt, cfg, elem_slice)._get()

        def __setitem__(self, index: int, _value: Any):
            option = object.__getattribute__(self, _K_OPTION)
            raise NotImplementedError(
                f"'{option._basename}' ('{option._path}') array elements can "
                "not be set directly!")

        def _get(self):
            """An access into a directory allows continuing to subelements."""
            return self

        def _set(self, _value: Any):
            option = object.__getattribute__(self, _K_OPTION)
            raise NotImplementedError(
                f"'{option._basename}' ('{option._path}') directory can not "
                "be set directly!")

    def _access(self, cfg: "Configuration", data_slice: Dict[str, Any]) \
            -> Any:
        return OptionDirectoryList._Access(self, cfg, data_slice)


class InvalidOptionValueError(ValueError):
    def __init__(self, option: OptionBase, value: Any):
        super().__init__(f"invalid value {str(value)} passed to option "
                         f"'{option._basename}' ('{option._path}')")


def _log_validation_failure_custom_message(message: str, option: OptionBase,
                                           _value: Any):
    LOG.error("Option '%s' ('%s'): %s",
              option._basename, option._path, message)


class ReadOnlyOptionError(AccessError):
    def __init__(self, option: OptionBase):
        super().__init__(f"option '{option._basename}' ('{option._path}') is "
                         "read-only!")


class RaiseIfUnset:
    """
    Tag type to indicate that accessing `Option`'s `default()` should
    ``raise`` if the value is not defined in the `Configuration` structure.
    """


class UnsetError(AccessError, KeyError):
    def __init__(self, option: OptionBase):
        super().__init__(f"option '{option._basename}' ('{option._path}') is "
                         "not set, and no suitable default value exists!")


class Option(OptionBase):
    """
    `Option`s encapsulate the access to leaf nodes of the configuration
    file, and return or assign their values in a raw form directly to the
    data backing memory.

    Note that an `Option` can still represent a complete `list` or `dict`, but
    using such means that client code accesses the collection as a single
    entity, without the configuration access layer associating further
    semantics to individual elements.
    """

    def __init__(self,
                 schema: "Schema",
                 name: Optional[str],
                 path: str,
                 description: Optional[str] = None,
                 default: Union[RaiseIfUnset,
                                None,
                                Any,
                                Callable[[], Any]] = RaiseIfUnset,
                 read_only: bool = True,
                 secret: bool = False,
                 validation_predicate: Optional[
                     Callable[[Any], bool]
                 ] = None,
                 validation_fail_action: Optional[
                     Union[Callable[[OptionBase, Any], None],
                           str]
                 ] = None,
                 supports_update: bool = True,
                 update_callback: Optional[
                     Callable[[OptionBase, str, Any, Any], None]
                 ] = None,
                 ):
        """
        Initialises an `Option`, setting up its behaviour.

        Accessing an `Option` for reading, when done through a `Configuration`
        structure, will return the value in the `Configuration`'s memory,
        unless the `Option` is not mapped.
        In that case, the `default` value is returned for reads, which may be
        a concrete value, a factory function returning a concrete value,
        `None`, or the special tag type `RaiseIfUnset`.
        If the default `default` choice, `RaiseIfUnset`, is used, then the
        unmappedness of the `Option` will raise the `UnsetError` to client
        code; otherwise, the appropriate default object, or the result of the
        factory function, is returned.

        If `read_only` is set to `False`, the option will be assignable with
        the usual ``__setattr__`` syntax.
        Note, that setting an `Option` only changes its value **IN MEMORY**,
        mutating the `Configuration` data structure, but **NOT** the file in
        storage.
        Note also, that Python does not support the verification of read-only
        status or a method for "const correctness" as thoroughly as other
        languages, such as C or C++.
        If the `Option` corresponds to a complex (but from the purview of the
        `configuration_access` library, unmanaged) data structure, such as a
        `list`, `read_only` will **NOT PREVENT** client code from calling
        mutators such as ``append()`` on the loaded entity.

        If the option is set to be `secret`, the values are not printed to
        the output during `LOG` messages from this library.
        The setting does not affect any other behaviour.

        When accessing the value, setting a new value, or updating via a
        reload, if set, the `validation_predicate` function is executed, which
        is expected to return `False` if the value is invalid based on some
        domain-specific criteria.
        If the validation fails, either the `str` message in
        `validation_fail_action` (or a default, if `None`) is logged, or, if
        `validation_fail_action` is a function, that callback is executed.

        After the callback has returned, invalid values will be handled in the
        following way:
            - Reading or setting an invalid value will result in a
            `InvalidOptionValueError` being raised.
            - Updating to an invalid value will keep the old value intact.

        By default, `Option`s support hot reloading, see
        `Configuration.reload()`.
        Following a reload, the value of the `Option` will be reflecting the
        changes ingested from the backing storage file.
        If `update_callback` is set to some function, it will be executed,
        passing both the old and the new value of the `Option`.
        Set `supports_update` to `False` to disable support for hot reloads.
        If disabled, changes to the underlying value will be detected and
        reported, but the reading accesses will still return the old value.
        """
        super().__init__(schema=schema, name=name, path=path,
                         description=description)

        self._default = default
        self._read_only = read_only
        self._secret = secret

        self._reload_update = supports_update
        self._update_callback = update_callback

        self._validator = validation_predicate
        self._fail_callback: Optional[Callable[[OptionBase, Any], None]] = None
        if validation_fail_action is None:
            self._fail_callback = _log_validation_failure
        elif isinstance(validation_fail_action, str):
            self._fail_callback = partial(
                _log_validation_failure_custom_message,
                validation_fail_action)
        else:
            self._fail_callback = validation_fail_action

        if self._default != RaiseIfUnset and self._validator is not None \
                and not self._validator(self.default):
            raise ValueError(f"Default value '{str(self.default)}' for "
                             f"option '{self._basename}' ('{self._path}') is "
                             "invalid according to the validation predicate "
                             "and should not be used!")

    def _get_children(self) -> OptionDict:
        raise NotImplementedError("'Option' is a leaf node.")

    class _Access(OptionBase._Access):
        """
        Allows retrieving and setting the value of a leaf configuration option.
        """

        def __init__(self, option: OptionBase, cfg: "Configuration",
                     data_slice: Dict[str, Any]):
            if not isinstance(data_slice, dict):
                raise TypeError("data captured in an access to a scalar "
                                "must offer reference semantics!")

            super().__init__(option=option, cfg=cfg, data_slice=data_slice)

        def _get(self):
            opt, cfg, ds = \
                cast(Option, object.__getattribute__(self, _K_OPTION)), \
                object.__getattribute__(self, _K_CONFIGURATION), \
                object.__getattribute__(self, _K_DATA_SLICE)
            try:
                value = ds[opt._basename]
            except KeyError:
                if opt.has_default:
                    return opt.default
                raise UnsetError(opt) from BackingDataError(opt, cfg)

            if not opt.run_validation(value):
                opt.run_validation_failure_action(value)
                raise InvalidOptionValueError(opt, value)

            return value

        def _set(self, value: Any):
            opt, ds = \
                cast(Option, object.__getattribute__(self, _K_OPTION)), \
                object.__getattribute__(self, _K_DATA_SLICE)

            if opt.is_read_only:
                raise ReadOnlyOptionError(opt)

            if not opt.run_validation(value):
                opt.run_validation_failure_action(value)
                raise InvalidOptionValueError(opt, value)

            ds[opt._basename] = value

    def _access(self, cfg: "Configuration", data_slice: Dict[str, Any]) \
            -> Any:
        return Option._Access(self, cfg, data_slice)

    @property
    def has_default(self) -> bool:
        return self._default != RaiseIfUnset

    @property
    def default(self) -> Optional[Any]:
        """Explicitly returns the default value for this `Option`."""
        if not self.has_default:
            raise UnsetError(self)
        if callable(self._default):
            return self._default()
        return self._default

    @property
    def is_read_only(self) -> bool:
        return self._read_only

    @property
    def is_secret(self) -> bool:
        return self._secret

    @property
    def is_updatable(self) -> bool:
        return self._reload_update

    def run_validation(self, value: Any) -> bool:
        """
        Executes the validation function of the `Option` and returns whether
        the provided `value` is valid.

        This method does not execute the "validation failure callback", see
        `run_validation_failure_action()` for that.
        """
        return not self._validator or self._validator(value)

    def run_validation_failure_action(self, value: Any):
        """
        Executes the `Option`'s validation failure callback action with the
        given `value` as the parameter.
        """
        if self._fail_callback:
            return self._fail_callback(self, value)
        return None

    def run_update_callback(self, path: str, old_value: Any, value: Any):
        """
        Executes the `Option`'s `update_callback` action with the specified
        values.
        """
        if self._update_callback:
            return self._update_callback(self, path, old_value, value)
        return None


def _value_or_secret(option: Option, value: Any) -> str:
    return "(secret!)" if option.is_secret else f"'{value}'"


def _log_validation_failure(option: OptionBase, value: Any) -> None:
    LOG.error("Invalid value %s passed to option '%s' ('%s')",
              '?' if not isinstance(option, Option)
              else _value_or_secret(option, value),
              option._basename, option._path)


class Schema:
    """
    A schema is a collection of `Option` objects, which allow checked,
    semantic access to a configuration data structure.
    This object is a set of proxies, essentially a glorified sack of pointer
    to data members.
    The actual configuration values are NOT stored in this object,
    see `Configuration`.
    """
    def __init__(self):
        # This code is frightening at first, but, unfortunately, the usual
        # 'self.member' syntax must be side-stepped such that __getattr__ and
        # __setattr__ can be implemented in a user-friendly way.
        object.__setattr__(self, _K_OPTIONS, {
            '/': OptionDirectory(
                schema=self,
                name=None,
                path='/',
                description="<Root of Schema>")
        })

    @property
    def options(self) -> OptionDict:
        return object.__getattribute__(self, _K_OPTIONS)

    @property
    def root(self) -> OptionDirectory:
        return cast(OptionDirectory, self.options['/'])

    def add_option(self,
                   name: Optional[str],
                   path: str,
                   parent: Optional[OptionDirectory] = None,
                   **kwargs) -> OptionBase:
        """
        Registers an `Option` in the current `Schema`.

        The apparent path of the to-be-created `Option` determines its type:
          - paths ending in ``"[]/"`` denote an `OptionDirectoryList`, which
            is a numbered list of `OptionDirectory`s, containing multiple
            instances of `Option`s.
          - paths ending in ``'/'`` denote an `OptionDirectory`.
          - everything else denotes an `Option`, which is a leaf value.

        If path begins with ``"./"``, the `parent` parameter should be set,
        and path is understood relative to the parent.
        By default, the `parent` is the same as the `Root` of the schema.

        Additional keyword arguments are forwarded to the `Option` constructor.
        """
        if path == '/':
            raise ValueError("The '/' root of the Option structure is "
                             "hard-coded and can not be manually added as "
                             "an option!")
        if not path.startswith(('/', "./")):
            raise ValueError(
                f"Path '{path}' must be a proper relative or absolute "
                "POSIX-y path")
        if path.endswith("[]"):
            raise ValueError(
                f"Path '{path}' designating an indexable sequence must use "
                "the directory syntax, and end with \"[]/\"")
        if ' ' in path:
            raise ValueError(f"Path '{path}' must not contain spaces")

        clazz: Type[OptionBase] = Option
        if path.endswith('/'):
            clazz = OptionDirectory
            path = path.rstrip('/')
            if path.endswith("[]"):
                clazz = OptionDirectoryList

        if path.startswith("./"):
            if parent is None:
                parent = self.root
            path = parent._path.rstrip('/') + '/' + path.replace("./", '', 1)

        options = object.__getattribute__(self, _K_OPTIONS)
        for parent_path in map(str, reversed(PurePosixPath(path).parents)):
            if parent_path not in options:
                raise KeyError(f"Parent OptionDirectory-like '{parent_path}' "
                               "is not registered")

        opt = clazz(self, name, path, **kwargs)
        if opt._path in options:
            raise KeyError(f"Option '{opt._path}' is already registered!")
        options[opt._path] = opt
        return opt


def _get_config_json(file_path: Path) -> Dict[str, Any]:
    LOG.debug("Reading configuration file '%s'...", file_path)
    config_dict = load_json(str(file_path), None)
    if config_dict is None:
        raise ValueError(
            f"Configuration file '{str(file_path)}' was invalid JSON. "
            "The log output contains more information.")
    LOG.debug("Loaded configuration file '%s'.", file_path)

    return config_dict


class ConfigurationUpdateFailureReason(Enum):
    UPDATE_UNSUPPORTED = Enumerator()
    VERIFICATION_FAILED = Enumerator()
    LIST_ELEMENT_ONLY_PARTIALLY_UPDATED = Enumerator()


class Configuration:
    """
    `Configuration` contains the memory-backed data structure loaded from a
    configuration file, and allows access to it through an established
    Schema.
    """

    ValidationResult = List[Tuple[str, Option]]
    UpdateResult = Tuple[List[Tuple[str, OptionBase, Any]],
                         List[Tuple[str, OptionBase,
                                    ConfigurationUpdateFailureReason]]
                         ]

    def __init__(self, schema: Schema, configuration: Dict[str, Any],
                 file_path: Path):
        """
        Initialise a new `Configuration` collection.

        The collection copies and takes ownership of the `configuration` data
        structure.
        """
        object.__setattr__(self, _K_CONFIGURATION, deepcopy(configuration))
        object.__setattr__(self, _K_FILE_PATH, file_path)
        object.__setattr__(self, _K_SCHEMA, schema)

    @classmethod
    def from_file(cls, schema: Schema, configuration_file: Path):
        """
        Initialise a new `Configuration` collection from the contents of a
        file.

        :param configuration_file: The configuration file to be read and
            parsed. This file *MUST* exist to initialise this instance.
            The file *MUST* be in JSON format, currently this is the only one
            supported.
        """
        return cls(schema,
                   _get_config_json(configuration_file),
                   configuration_file)

    @classmethod
    def from_memory(cls, schema: Schema, config_dict: Dict[str, Any]):
        """
        Initialise a new `Configuration` collection from the contents of a
        data structure in memory.

        The ceated data structure is deep-copied and does not alias
        the parameter.
        """
        return cls(schema, config_dict,
                   PosixPath(f"/mem/@{hex(id(config_dict))}"))

    def __dir__(self):
        """
        Allows ``dir(...)`` to list the top-level children of the
        `Configuration`.
        """
        return sorted(set(
            cast(List[Any], dir(super())) +
            cast(List[Any], list(self.__dict__.keys())) +
            cast(List[Any], list(self._schema.root._get_children().keys()))
        ))

    @property
    def _file_path(self) -> Optional[Path]:
        """Returns the file path from which the `Configuration` was loaded."""
        path = object.__getattribute__(self, _K_FILE_PATH)
        return path if not str(path).startswith("/mem/@") else None

    @property
    def _schema(self) -> Schema:
        """Returns the `Schema` used as the schema of the `Configuration`."""
        return object.__getattribute__(self, _K_SCHEMA)

    def __getattr__(self, name: str) -> OptionBase:
        """
        Starts the accessing descent of the `Configuration` using the object
        member access ``.`` (dot) operator.
        """
        data: dict = object.__getattribute__(self, _K_CONFIGURATION)
        return getattr(self._schema.root._access(self, data), name)

    def __setattr__(self, name: str, value: Any):
        """
        Helper method that makes configuration options settable through
        assigning a member accessed via the ``.`` (dot) operator.
        """
        data: dict = object.__getattribute__(self, _K_CONFIGURATION)
        return setattr(self._schema.root._access(self, data), name, value)

    def _validate(self,
                  execute_validation_failure_callbacks: bool = True
                  ) -> ValidationResult:
        """
        Checks all `Option`s in the current `Configuration` for their validity,
        as specified by `Option.validation_predicate`, and returns the list of
        those that failed.

        If `execute_validation_failure_callbacks` is `True`, the
        "validation failure action" callbacks will be called for each failing
        `Option`, fully simulating the normal behaviour of reading an `Option`
        with an invalid value.

        Despite, this function **never** raises the `InvalidOptionValueError`.
        """
        failed_options: List[Tuple[str, Option]] = []

        def _traverse(path: PurePosixPath,
                      opt: OptionBase,
                      data_slice: dict):
            if isinstance(opt, OptionDirectoryList):
                try:
                    list_slice = data_slice[opt._basename]
                except KeyError:
                    return

                for i, e in enumerate(list_slice):
                    child_path = path / str(i)
                    _traverse(child_path,
                              OptionDirectory(opt._schema_,
                                              opt._name,
                                              opt._path,
                                              opt._description),
                              # Construct a top-level data slice for one
                              # element of the list.
                              {f"{opt._basename}[]": e})
                return
            if isinstance(opt, OptionDirectory):
                try:
                    directory_slice = data_slice[opt._basename]
                except KeyError:
                    directory_slice = {}

                for child in opt._get_children().values():
                    child_path = path / child._basename
                    try:
                        # Construct a data slice for the recursing child.
                        # This method only reads the values, so it is not a
                        # problem that references are not bound here.
                        child_slice = {child._basename:
                                       directory_slice[child._basename]}
                    except KeyError:
                        child_slice = {}
                    _traverse(child_path, child, child_slice)
                return
            if isinstance(opt, Option):
                try:
                    value = data_slice[opt._basename]
                except KeyError:
                    if not opt.has_default:
                        if execute_validation_failure_callbacks:
                            opt.run_validation_failure_action(None)
                        failed_options.append((str(path), opt))

                    # If there is a default, Option's constructor took care of
                    # ensuring that the default passes validation.
                    return

                if not opt.run_validation(value):
                    failed_options.append((str(path), opt))
                    if execute_validation_failure_callbacks:
                        opt.run_validation_failure_action(value)
                return

            raise NotImplementedError(
                f"Unhandled Option type: {str(type(opt))}")

        root = cast(OptionDirectory, self._schema.root)
        _traverse(PurePosixPath(root._path), root,
                  {root._basename:
                   object.__getattribute__(self, _K_CONFIGURATION)})
        return failed_options

    def _update(self) -> UpdateResult:
        """
        Updates the `Configuration` automatically from the last used backing
        file, as available in `file_path`, if it was loaded from one.
        Otherwise, it does nothing.
        """
        return self._update_from_file(self._file_path) if self._file_path \
            else ([], [])

    def _update_from_file(self, configuration_file: Path) -> UpdateResult:
        """
        Updates the `Configuration` from the specified `configuration_file`,
        and sets `file_path` to point at this new file instead.
        """
        LOG.info("Start updating configuration from file '%s'...",
                 configuration_file)
        ret = self._update_from_memory(_get_config_json(configuration_file))
        object.__setattr__(self, _K_FILE_PATH, configuration_file)
        return ret

    def _update_from_memory(self, config_dict: Dict[str, Any]) \
            -> UpdateResult:
        """
        Updates the `Configuration` with the contents of the specified
        `config_dict`.

        During an update, the `config_dict` structure is walked recursively,
        according to the `Schema` of the `Configuration`.
        For each changed value that does not match the corresponding value in
        the currently loaded configuration data structure, the change is
        validated according to `Option.validation_predicate`.
        If the validation succeeds, the change is "merged" into the data owned
        by `self`; otherwise, the old value is kept intact and the `Option` is
        returned as a failing reload,
        see `ConfigurationUpdateFailureReason.VERIFICATION_FAILED`.

        If `Option.update_callback` is set for a successfully updated
        `Option`, it is fired accordingly passing the `Option` instance,
        the old, and the new value.

        Updates are only carried out for `Option`s that have their
        `Option.supports_update` flag set to `True`.
        Otherwise, if a non-updatable value still in fact changed when
        differentiating the `self._configuration` and `config_dict`, this
        is logged, but the old value is kept intact.

        Returns the `Option`s that changed value, and that failed to update.
        """
        LOG.info("Start updating configuration ...")
        unsuccessful_updates: List[Tuple[
            str, OptionBase, ConfigurationUpdateFailureReason]] = []

        def _traverse(path: PurePosixPath,
                      opt: OptionBase,
                      self_data_slice: dict,
                      new_data_slice: dict) -> Tuple[
                          bool,
                          List[Tuple[str, OptionBase, Any]],
                          List[Tuple[Option, str, Any, Any]]
                      ]:
            updated_options: List[Tuple[str, OptionBase, Any]] = []
            update_callbacks_to_run: List[Tuple[Option, str, Any, Any]] = []
            if isinstance(opt, OptionDirectoryList):
                success = True
                # Updating lists is more convoluted than fixed trees.
                # Unfortunately, lists do not have a key beyond an index, so
                # identifying changes in configuration would be more involved,
                # and impossible in the general case, as new list elements
                # could be added BEFORE existing ones, removed all over the
                # place, and "swapping" two elements shows up as potentially
                # all fields changing in both affected elements.
                #
                # This poses a problem if an inner OptionDirectory tree can
                # only partially update.
                # Such would result in, e.g., if the "username" is missing
                # from an authentication-like configuration where such is
                # invalid result in keeping the old "username" in the run-time
                # but using the new "password", which would clearly botch the
                # sanity of the running process.
                #
                # Instead, we will collect the result values in a separate
                # list, and save the modified element only if it was fully
                # updateable.
                # In every other case, the already in-memory value will be
                # kept active.
                list_slice_result: List[Dict[Any, Any]] = []
                try:
                    list_slice_self = self_data_slice[_K_REF][opt._basename]
                except KeyError:
                    list_slice_self = []

                try:
                    list_slice_new = new_data_slice[_K_REF][opt._basename]
                except KeyError:
                    list_slice_new = []

                if len(list_slice_self) != len(list_slice_new):
                    LOG.warning("Length of list option '%s' ('%s') changed "
                                "from %d to %d.",
                                opt._name, path,
                                len(list_slice_self), len(list_slice_new))

                success = True
                for idx in range(0, min(len(list_slice_self),
                                        len(list_slice_new))):
                    child_path = path / str(idx)
                    child_old_value = deepcopy(list_slice_self[idx])

                    # Construct top-level data slices for the current and new
                    # data to simulate directory access in the recursion.
                    directory_slice_self = {_K_REF: {f"{opt._basename}[]":
                                                     list_slice_self[idx]}}
                    directory_slice_new = {_K_REF: {f"{opt._basename}[]":
                                                    list_slice_new[idx]}}

                    child_success, child_updates, child_callbacks = \
                        _traverse(child_path,
                                  OptionDirectory(opt._schema_,
                                                  opt._name,
                                                  opt._path,
                                                  opt._description),
                                  directory_slice_self,
                                  directory_slice_new)

                    if child_success:
                        # If the update was successful, "directory_slice_self"
                        # will have the updated data patched in.
                        list_slice_result.append(
                            directory_slice_self[_K_REF][
                                f"{opt._basename}[]"])
                        updated_options.extend(child_updates)
                        update_callbacks_to_run.extend(child_callbacks)
                    else:
                        success = False
                        unsuccessful_updates.append((
                            str(child_path), opt,
                            ConfigurationUpdateFailureReason.
                            LIST_ELEMENT_ONLY_PARTIALLY_UPDATED))
                        LOG.error("Failed to update a configuration option "
                                  "in an element of the list option "
                                  "'%s' ('%s') at index %d. "
                                  "The entire list element will retain its "
                                  "**OLD VALUE**!",
                                  opt._name, path, idx)
                        list_slice_result.append(child_old_value)

                self_data_slice[_K_REF][opt._basename] = list_slice_result
                return success, updated_options, update_callbacks_to_run
            if isinstance(opt, OptionDirectory):
                try:
                    directory_slice_self = \
                        self_data_slice[_K_REF][opt._basename]
                except KeyError:
                    directory_slice_self = {}

                try:
                    directory_slice_new = \
                        new_data_slice[_K_REF][opt._basename]
                except KeyError:
                    directory_slice_new = {}

                success = True
                for child in opt._get_children().values():
                    child_path = path / child._basename

                    # Construct data slices for the children by binding the
                    # entire parent collection behind a reference, as the
                    # child Option handling will usually **WRITE** into this
                    # data structure.
                    child_slice_self = {_K_REF: directory_slice_self}
                    child_slice_new = {_K_REF: directory_slice_new}

                    child_success, child_updates, child_callbacks = \
                        _traverse(child_path, child,
                                  child_slice_self, child_slice_new)
                    success = success and child_success
                    updated_options.extend(child_updates)
                    update_callbacks_to_run.extend(child_callbacks)

                # It might be that an entire OptionDirectory tree happens to
                # be added with the update(), and was not present originally.
                # In that case, directory_slice_self was a local dict()
                # literal, not part of the full configuration tree, so it has
                # to be added now.
                self_data_slice[_K_REF][opt._basename] = directory_slice_self
                return success, updated_options, update_callbacks_to_run
            if isinstance(opt, Option):
                old_value, new_value = None, None
                try:
                    old_value = self_data_slice[_K_REF][opt._basename]
                    old_value_exists = True
                except KeyError:
                    old_value_exists = opt.has_default
                    if old_value_exists:
                        old_value = opt.default

                try:
                    new_value = new_data_slice[_K_REF][opt._basename]
                    new_value_exists = True
                except KeyError:
                    new_value_exists = opt.has_default
                    if new_value_exists:
                        new_value = opt.default

                if (not old_value_exists and not new_value_exists) \
                        or old_value == new_value:
                    # There are no changes to the value (either explicitly,
                    # or the values were matching the defaults).
                    return True, [], []

                if not new_value_exists:
                    # The value is gone from the new configuration object, and
                    # "lack of value" would default to throwing.
                    LOG.error("Value of configuration option '%s' ('%s') "
                              "missing from updated configuration, but "
                              "it is invalid to not have this value set!",
                              opt._name, path)
                    LOG.info("Configuration option '%s' ('%s') will keep its "
                             "**OLD VALUE**: %s",
                             opt._name, path,
                             _value_or_secret(opt, old_value))
                    unsuccessful_updates.append(
                        (str(path), opt,
                         ConfigurationUpdateFailureReason.VERIFICATION_FAILED))
                    return False, [], []

                if not opt.is_updatable:
                    LOG.error("Value of configuration option '%s' ('%s') "
                              "observed change from %s to %s, "
                              "but it does NOT support hot (online) changes. "
                              "You will need to re-run CodeChecker for the "
                              "change to have an effect!",
                              opt._name, path,
                              _value_or_secret(opt, old_value),
                              _value_or_secret(opt, new_value))
                    LOG.info("Configuration option '%s' ('%s') will keep its "
                             "**OLD VALUE**: %s",
                             opt._name, path,
                             _value_or_secret(opt, old_value))
                    unsuccessful_updates.append(
                        (str(path), opt,
                         ConfigurationUpdateFailureReason.UPDATE_UNSUPPORTED))
                    return False, [], []

                if not opt.run_validation(new_value):
                    opt.run_validation_failure_action(new_value)
                    LOG.error("Value of configuration option '%s' ('%s') "
                              "observed change from %s to %s, "
                              "but the new value is invalid!",
                              opt._name, path,
                              _value_or_secret(opt, old_value),
                              _value_or_secret(opt, new_value))
                    LOG.info("Configuration option '%s' ('%s') will keep its "
                             "**OLD VALUE**: %s",
                             opt._name, path,
                             _value_or_secret(opt, old_value))
                    unsuccessful_updates.append(
                        (str(path), opt,
                         ConfigurationUpdateFailureReason.VERIFICATION_FAILED))
                    return False, [], []

                LOG.warning("Value of configuration option '%s' ('%s') "
                            "changed from %s to %s!",
                            opt._name, path,
                            _value_or_secret(opt, old_value),
                            _value_or_secret(opt, new_value))
                self_data_slice[_K_REF][opt._basename] = new_value
                return True, [(str(path), opt, new_value)], \
                    [(opt, str(path), old_value, new_value)]

            raise NotImplementedError(
                f"Unhandled Option type: {str(type(opt))}")

        root = cast(OptionDirectory, self._schema.root)
        _, updated_options, update_callbacks_to_run = \
            _traverse(PurePosixPath(root._path), root,
                      # Craft data slices that encapsulate the parent
                      # "directory" such that the changes to the in-memory
                      # configuration can be done through the usual reference
                      # semantics.
                      {_K_REF: {
                          root._basename:
                          object.__getattribute__(self, _K_CONFIGURATION)}},
                      {_K_REF: {root._basename: config_dict}})

        for opt, path, old, new in update_callbacks_to_run:
            opt.run_update_callback(path, old, new)

        LOG.info("Done updating configuration file.")
        return updated_options, unsuccessful_updates
