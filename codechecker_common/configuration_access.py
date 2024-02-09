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
from pathlib import Path, PurePosixPath
from typing import cast, Any, Callable, Dict, List, Optional, TypeVar, Union

from .logger import get_logger
from .util import load_json


LOG = get_logger("system")

_K_FILE_PATH = "__file_path"
_K_CONFIGURATION = "__configuration"
_K_OPTIONS = "__options"
_K_SCHEMA = "__schema"

_T_CONFIGURATION = TypeVar("_T_CONFIGURATION", bound="Configuration")
_T_OPTION_BASE = TypeVar("_T_OPTION_BASE", bound="OptionBase")
_T_SCHEMA = TypeVar("_T_SCHEMA", bound="Schema")

OptionDict = Dict[str, _T_OPTION_BASE]


class AccessError(Exception):
    pass


class BackingDataError(AccessError):
    def __init__(self, option: _T_OPTION_BASE, cfg: _T_CONFIGURATION):
        super().__init__(
            f"'{option.basename}' ('{option.path}') not found in "
            f"configuration file '{cfg.file_path}'")


class BackingDataIndexError(AccessError, IndexError):
    def __init__(self, option: _T_OPTION_BASE, cfg: _T_CONFIGURATION,
                 index: int, count: int):
        super().__init__(
            f"list index {index} out of range for '{option.basename}' "
            f"('{option.path}'), only {count} elements exist")


def _get_children_options(parent_path: str, options: OptionDict) \
        -> OptionDict:
    if not parent_path.endswith('/'):
        parent_path = parent_path + '/'
    keys = set(map(lambda p: p[len(parent_path):].split('/')[0],
                   filter(lambda p: p.startswith(parent_path), options)))
    opts = [options[parent_path + k] for k in keys if k != '']
    children = {o.basename: o for o in opts}
    return children


def _step_into_child(option, cfg: _T_CONFIGURATION, name: str):
    try:
        child_option = option.get_children()[name]
    except KeyError:
        raise AttributeError(
            f"'{option.path}' option has no attribute '{name}'")

    try:
        access = getattr(child_option, "_access")
        return access
    except AttributeError:
        raise AttributeError(f"'{child_option.path}' option is not accessible")


class OptionBase:
    def __init__(self,
                 schema: _T_SCHEMA,
                 name: Optional[str],
                 path: str,
                 description: Optional[str] = None):
        """
        Instantiates a new Option (base class) which designates, under a
        user-facing 'name', an element accessible in a configuration
        dictionary, as specified by 'path'. '/' is the root of the
        configuration dictionary, and each "directory" is a named key in a
        sub-dictionary.

        The Option class hierarchy implement accessor classes, which deal with
        a type-safe and semantically correct reading of the specified values,
        but do not own or store the actual value of the option. An underlying
        storage object (almost certainly a Dict) is always required during
        actual value access.

        For example, "/max_run_count" denotes the child of the top level
        dict, whereas "/keepalive/enabled" is a child of a sub-tree.
        """
        self._schema = schema
        self._name = name
        self._description = description
        self._path = path

    @property
    def name(self) -> str:
        return self._name if self._name is not None else f"<{self.path}>"

    @property
    def description(self) -> Optional[str]:
        return self._description

    @property
    def path(self) -> str:
        return self._path

    @property
    def basename(self) -> str:
        return PurePosixPath(self._path).name

    def get_children(self) -> OptionDict:
        """
        Returns the options that are registered as children of the current
        Option in the schema.
        """
        raise NotImplementedError(f"{str(type(self))} can not have children")

    class _Access:
        """
        The abstract base class to represent an ongoing access into a loaded
        Configuration, based on an established Schema.

        When using the member . (dot) operator on a Configuration, instances
        of this _Access class are created, allowing the client code to
        continue descending into potential inner attributes.

        This base class does nothing, apart from storing references to the
        core objects it was originally instantiated with.
        """
        def __init__(self, option: _T_OPTION_BASE, cfg: _T_CONFIGURATION,
                     data_slice):
            self._option = option
            self._configuration = cfg
            self._data_slice = data_slice

        def _get(self) -> Any:
            raise NotImplementedError(
                f"{str(type(self._option))} can not be get!")

        def _set(self, new_value: Any) -> Any:
            raise NotImplementedError(
                f"{str(type(self._option))} can not be set!")

    def _access(self, cfg: _T_CONFIGURATION, data_slice) -> Any:
        # pylint: disable=unused-argument
        raise NotImplementedError(f"{str(type(self))} can not be accessed")


class OptionDirectory(OptionBase):
    """
    Represents a collection group of options, corresponding to the "directory"
    concept in filesystems. A directory may only contain sub-options and
    metadata, and has no value unto itself.
    """
    def __init__(self,
                 schema: _T_SCHEMA,
                 name: Optional[str],
                 path: str,
                 description: Optional[str] = None):
        super().__init__(schema=schema, name=name, path=path,
                         description=description)

    def add_option(self, name: Optional[str], path: str, *args, **kwargs):
        """
        Adds an option with the given name and sub-path, relative to the
        current directory. See Schema.add_option() for details.
        """
        if not path.startswith("./"):
            raise ValueError("path must be relative to OptionDirectory")

        return self._schema.add_option(name=name,
                                       path=path,
                                       parent=self,
                                       *args, **kwargs)

    def get_children(self) -> OptionDict:
        return _get_children_options(self.path, self._schema._options)

    class _Access(OptionBase._Access):
        """
        Allows accessing, as attributes, the first-level children of
        "directories" (option groups).
        """
        def __init__(self, option: _T_OPTION_BASE, cfg: _T_CONFIGURATION,
                     data_slice: Any):
            if option.basename != '':
                try:
                    data_slice = data_slice[option.basename]
                except KeyError:
                    raise BackingDataError(option, cfg)

            super().__init__(option=option, cfg=cfg, data_slice=data_slice)

        def __dir__(self):
            """
            Allows dir(...) to list the available children options' names.
            """
            return sorted(set(
                cast(List[Any], dir(super())) +
                cast(List[Any], list(self.__dict__.keys())) +
                cast(List[Any], list(self._option.get_children().keys()))
            ))

        def __getattr__(self, name: str):
            """
            Continues the accessing descent of the Configuration using the
            object member access . (dot) operator.
            """
            access_ctor = _step_into_child(self._option,
                                           self._configuration,
                                           name)
            return access_ctor(self._configuration, self._data_slice)._get()

        def _get(self):
            """An access into a directory allows continuing to subelements."""
            return self

    def _access(self, cfg: _T_CONFIGURATION, data_slice) -> Any:
        return OptionDirectory._Access(self, cfg, data_slice)


class OptionDirectoryList(OptionDirectory):
    """
    Represents a special kind of OptionDirectory that acts as a "template" for
    inner Options. In a group, multiple copies of the same inner structure may
    exist, and each instance is accessible in practice by specifying a numeric
    index of the instance.

    Registered under the abstract path
    "/authentication/method_ldap/authorities[]", this type takes care of
    requiring an index to access the children instances of this directory.
    """
    def __init__(self,
                 schema: _T_SCHEMA,
                 name: Optional[str],
                 path: str,
                 description: Optional[str] = None):
        super().__init__(schema=schema, name=name, path=path,
                         description=description)

    @property
    def basename(self) -> str:
        return PurePosixPath(self._path).name.replace("[]", '', 1)

    class _Access(OptionDirectory._Access):
        """
        Allows accessing, as if members of a list, the first-level children of
        "directories" (option groups).
        """
        def __init__(self, option: _T_OPTION_BASE, cfg: _T_CONFIGURATION,
                     data_slice):
            super().__init__(option=option, cfg=cfg, data_slice=data_slice)

        def __dir__(self):
            return sorted(set(
                cast(List[Any], dir(OptionBase._Access)) +
                cast(List[Any], list(self.__dict__.keys()))
            ))

        def __getattr__(self, name: str):
            raise NotImplementedError("Accessing an array of schema elements "
                                      "must use the subscript operator []")

        def __len__(self) -> int:
            """Returns the number of child elements in the option list."""
            return len(self._data_slice)

        def __getitem__(self, index: int):
            """
            Continues the accessing descent of the Configuration using the
            object indexing [] operator.
            """
            try:
                # Wrap the reference to the da of the single element into a
                # pseudo-directory structure that contains the data as if
                # it was not the child of a list at all.
                elem_slice = {self._option.basename: self._data_slice[index]}
            except IndexError:
                raise BackingDataIndexError(self._option, self._configuration,
                                            index, len(self._data_slice))

            # The indexed element of a directory list is a single directory.
            return OptionDirectory._Access(self._option,
                                           self._configuration,
                                           elem_slice)._get()

        def _get(self):
            """An access into a directory allows continuing to subelements."""
            return self

    def _access(self, cfg: _T_CONFIGURATION, data_slice) -> Any:
        return OptionDirectoryList._Access(self, cfg, data_slice)


class ScalarOption(OptionBase):
    """
    Scalar options encapsulate the access to leaf nodes of the configuration
    file, and return or assign their values in a raw form directly to the
    data backing memory.

    Note that a ScalarOption can still be a list or dict, but using such means
    that client code accesses the list as a single entity, without the
    configuration access layer associating semantics with the entry.
    """
    def __init__(self,
                 schema: _T_SCHEMA,
                 name: Optional[str],
                 path: str,
                 description: Optional[str] = None):
        super().__init__(schema=schema, name=name, path=path,
                         description=description)

    class _Access(OptionBase._Access):
        """
        Allows retrieving and setting the value of a leaf configuration option.
        """
        def __init__(self, option: _T_OPTION_BASE, cfg: _T_CONFIGURATION,
                     data_slice):
            if not isinstance(data_slice, dict):
                raise TypeError("data captured in an access to a scalar "
                                "must offer reference semantics!")

            super().__init__(option=option, cfg=cfg, data_slice=data_slice)

        def _get(self):
            try:
                return self._data_slice[self._option.basename]
            except KeyError:
                raise BackingDataError(self._option, self._configuration)

    def _access(self, cfg: _T_CONFIGURATION, data_slice) -> Any:
        return ScalarOption._Access(self, cfg, data_slice)


class _OLD_Option:
    """
    Encapsulates a configuration option which can be accessed by client
    code, optionally assigned, or even explicitly reloaded from the
    backing storage, should that change.
    """

    class CheckFailedError(Exception):
        def __init__(self, name: str):
            super().__init__("%s:@check() failed!" % name)

    class ReadOnlyError(AccessError):
        def __init__(self, name: str):
            super().__init__("'%s' is read-only" % name)

    class NotUpdatableError(AccessError):
        def __init__(self, name: str):
            super().__init__("'%s' is not updatable dynamically" % name)

    class ErrorIfUnset:
        """
        Tag type to indicate that getting the value of an Option if it is
        not explicitly configured should raise an error. This must be passed
        to the 'default' constructor parameter of Option.
        """
        def __init__(self):
            pass

    def __init__(self, name: str,
                 path: str,
                 default: Union[ErrorIfUnset, None, Any,
                                Callable[[], Any]] = ErrorIfUnset,
                 check: Optional[Callable[[Any], bool]] = None,
                 check_fail_msg: Optional[Union[Callable[[], str],
                                                str]] = None,
                 settable: bool = False,
                 updatable: bool = False,
                 description: Optional[str] = None):
        """
        If the accessed element is a list, numeric indices
        must be used to address individual elements, after which dictionary
        dereferencing can continue.

        If the accessing fails to get the elements of the configuration
        dictionary and a 'KeyError' or 'IndexError' is hit, the 'default'
        value, or the result of the 'default' function, if any, is returned.
        If 'default' is left as its default 'ErrorIfUnset()' option, the error
        is explicitly raised to client code.

        'check' is an optional callback that is executed every time a
        non-default configuration option is read or a 'settable' option is set.
        During reading, if 'check' returns False or throws, the configured
        value will be considered bogus, and will be replaced by the 'default'.
        If 'default' is unset and 'check' fails, a ValueError is raised
        unconditionally. Setting a value that makes 'check' fail is not
        allowed, and results in a ValueError.

        In any case, if 'check' fails and 'check_fail_msg' is set, it is
        printed to the output LOG as a warning. If 'check_fail_msg' is a
        function, the function is called and its return value is printed to
        the output LOG.


        If the Option is 'settable', clients will be allowed to change the
        Option's value, and that change is kept **IN MEMORY** for
        subsequent reads.

        If the Option is 'updatable', the external Configuration Manager
        will respect the change to the Option's value when the
        configuration is reloaded, see 'reload()'. A change observed
        through a reload will be logged for auditing purposes!

        Writing to the source of the configuration in a persistent fashion
        is **NOT SUPPORTED**!
        """
        self._allow_set = settable
        self._allow_update = updatable
        self._default = default
        self._check = check
        self._check_fail_msg = check_fail_msg

    @property
    def has_default(self) -> bool:
        return self._default != Option.ErrorIfUnset

    @property
    def default(self) -> Optional[Any]:
        if not self.has_default:
            raise KeyError("%s@default" % self.name)
        if callable(self._default):
            return self._default()
        return self._default

    @property
    def is_writable(self) -> bool:
        return self._allow_set

    @property
    def is_dynamically_updatable(self) -> bool:
        return self._allow_update

    @classmethod
    def __set_leaf(cls, parent: Union[Dict, List], name: str, value: Any):
        """
        Assigns 'value' to the leaf node, as identified by 'name',
        contained within the 'parent'.

        This is an internal method which does not validate whether the value
        is appropriate or whether the value may be set by client code!
        """
        if type(parent) is dict:
            cast(Dict, parent)[name] = value
        elif type(parent) is list:
            try:
                idx = int(name)
                try:
                    cast(List, parent)[idx] = value
                except IndexError:
                    raise KeyError(str(idx))
            except ValueError:
                raise
        else:
            raise TypeError("Non-subscriptable parent object type: %s"
                            % str(type(parent)))

    def _run_check(self, value: Any) -> bool:
        if not self._check:
            return True
        if not self._check(value):
            if self._check_fail_msg:
                msg = self._check_fail_msg
                if callable(msg):
                    msg = msg()
                LOG.warning("Configuration invariant check() failed: %s", msg)
            raise self.CheckFailedError(self._name)
        return True

    def __call__(self, configuration: Dict) -> Optional[Any]:
        """Reads and returns the value of the Option."""
        try:
            parent = self._descend_to_closest_parent(configuration)
            value = self.__get_leaf(parent, self._path.name)

            try:
                self._run_check(value)
            except Exception:
                if not self.has_default:
                    raise ValueError("check() failed for '%s'" % self.name)
                LOG.warning("check() failed for value of '%s', substituting "
                            "with the default value.", self.name)
                value = self.default

            return value
        except KeyError:
            if not self.has_default:
                raise KeyError("%s (%s) with no default set in configuration"
                               % (self.name, self.path))
            return self.default

    def set(self, configuration: Dict, value: Any):
        """
        Sets the value of the current Option in the given configuration data
        structure to 'value'. Calling this method is only valid if the Option
        is 'settable'.
        """
        if not self._allow_set:
            raise self.ReadOnlyError(self._name)
        try:
            self._run_check(value)
        except Exception:
            raise ValueError("Assigning value '%s' to '%s' would break "
                             "its check() invariant!"
                             % (str(value), self._name))

        try:
            parent = self._descend_to_closest_parent(configuration)
        except KeyError:
            raise KeyError("Descent failed, invalid path: '%s'"
                           % str(self._path))
        self.__set_leaf(parent, self._path.name, value)

    def _update(self, configuration: Dict, new_configuration: Dict):
        """
        Updates the value of the current Option in the old 'configuration'
        data structure to the value found in 'new_configuration', if the Option
        is updatable.
        """
        if not self._allow_update:
            raise self.NotUpdatableError(self._name)

        new_value = self(new_configuration)
        try:
            self._run_check(new_value)
        except Exception:
            raise ValueError("Updating '%s' to new value '%s' would break "
                             "its check() invariant!"
                             % (self._name, str(new_value)))

        try:
            parent = self._descend_to_closest_parent(configuration)
        except KeyError:
            raise KeyError("Descent failed, invalid path: '%s'"
                           % str(self._path))
        self.__set_leaf(parent, self._path.name, new_value)


class Schema:
    """
    A schema is a collection of Option objects, which allow checked, semantic
    access to a configuration data structure. This object is a set of proxies,
    essentially a glorified sack of pointer to data members. The actual
    configuration values are NOT stored in this object, see Configuration.
    """
    def __init__(self):
        # This code is frightening at first, but, unfortunately, the usual
        # 'self.member' syntax must be side-stepped so that __getattr__ and
        # __setattr__ can be implemented in a user-friendly way.
        object.__setattr__(self, _K_OPTIONS, {
            '/': OptionDirectory(
                schema=self,
                name=None,
                path='/',
                description="<Root of Schema>")
        })

    @property
    def _options(self) -> Dict[str, _T_OPTION_BASE]:
        return self.__dict__[_K_OPTIONS]

    @property
    def Root(self) -> OptionDirectory:
        return self.__dict__[_K_OPTIONS]['/']

    def add_option(self, name: Optional[str], path: str,
                   parent: Optional[OptionDirectory] = None,
                   *args, **kwargs):
        """
        Registers an Option in the current Schema.

        The apparent path of the to-be-created Option determines its type:
          - paths ending in "[]/" denote an MultiOptionGroup, which is a
            numbered list of OptionDirectories, containing multiple instances
            of Options
          - paths ending in '/' denote an OptionDirectory
          - everything else denotes a ScalarOption, which is a leaf value

        If path begins with "./", the parent parameter MUST be set, and
        path is understood relative to the parent.

        Additional positional and keyword arguments are forwarded to the
        Option constructors.
        """
        if path == '/':
            raise ValueError("The root of the Option structure is hard-coded "
                             "and can not be manually added as an option")
        if not path.startswith(('/', "./")):
            raise ValueError("Path must be a proper relative or absolute "
                             "POSIX-y path")
        if path.endswith("[]"):
            raise ValueError("Paths designating an indexable sequence must "
                             "use the directory syntax, and end with \"[]/\"")

        clazz = ScalarOption
        if path.endswith('/'):
            clazz = OptionDirectory
            path = path.rstrip('/')
            if path.endswith("[]"):
                clazz = OptionDirectoryList

        if path.startswith("./"):
            if parent is None:
                raise ValueError("parent must be specified for relative "
                                 "paths")
            path = parent.path.rstrip('/') + '/' + path.replace("./", '', 1)

        for parent_path in map(str,
                               reversed(PurePosixPath(path).parents)):
            if parent_path not in self.__dict__[_K_OPTIONS]:
                raise KeyError(f"Parent OptionDirectory-like '{parent_path}' "
                               "is not registered")

        opt = clazz(self, name, path, *args, **kwargs)
        self.__dict__[_K_OPTIONS][opt.path] = opt
        return opt


class Configuration:
    """
    Configuration contains the memory-backed data structure loaded from a
    configuration file, and allows access to it through an established
    Schema.
    """
    def __init__(self, schema: Schema, configuration_file: Path):
        """
        Initialise a new Configuration collection.

        :param configuration_file: The configuration file to be read and
            parsed. This file *MUST* exist to initialise this instance.
            The file *MUST* be in JSON format, currently this is the only one
            supported.
        """
        LOG.debug("Reading configuration file '%s'...", configuration_file)
        config_dict = load_json(str(configuration_file), None)
        if not config_dict:
            raise ValueError("Configuration file '%s' was invalid JSON. "
                             "The log output contains more information."
                             % str(configuration_file))
        LOG.debug("Loaded configuration file '%s'.", configuration_file)

        object.__setattr__(self, _K_SCHEMA, schema)
        object.__setattr__(self, _K_FILE_PATH, configuration_file)
        object.__setattr__(self, _K_CONFIGURATION, config_dict)

    def __dir__(self):
        """
        Allows dir(...) to list the top-level children of the Configuration.
        """
        schema = self.__dict__[_K_SCHEMA]
        return sorted(set(
            cast(List[Any], dir(super())) +
            cast(List[Any], list(self.__dict__.keys())) +
            cast(List[Any], list(schema.Root.get_children().keys()))
        ))

    @property
    def file_path(self) -> Path:
        """Returns the file path from which the Configuration was loaded."""
        return self.__dict__[_K_FILE_PATH]

    def __getattr__(self, name: str) -> _T_OPTION_BASE:
        """
        Starts the accessing descent of the Configuration using the object
        member access . (dot) operator.
        """
        schema = self.__dict__[_K_SCHEMA]
        data = self.__dict__[_K_CONFIGURATION]
        return getattr(schema.Root._access(self, data), name)

    def __setattr__(self, name: str, value):
        """
        Helper method that makes configuration options settable through
        assigning a member accessed via the . (dot) operator.
        """
        options = self.__dict__[_K_OPTIONS]
        option: Optional[Option] = None
        try:
            option = options[name]
        except KeyError:
            # If the options dict did not contain the requested key, consider
            # it as if it did not exist at all.
            raise AttributeError(name)

        # The inability to actually write the value of the option is a
        # different type of error.
        configuration = self.__dict__[_K_CONFIGURATION]
        cast(Option, option).set(configuration, value)

    def reload(self) -> List[str]:
        """
        Reloads and updates the configuration data structure in memory from
        the values that are present in the persisted configuration file the
        object was originally constructed with.

        Only Options that are marked 'updatable' are actually updated,
        following which the updated value is returned to subsequent clients.

        Returns the names of Options that changed their value due to the
        reload.
        """
        updated_opts: List[str] = list()
        LOG.info("Start reloading configuration file '%s'...", self.file_path)

        current_cfg = self.__dict__[_K_CONFIGURATION]
        config_file = self.__dict__[_K_FILE_PATH]
        new_cfg = load_json(config_file, None)
        if not new_cfg:
            raise ValueError("Configuration file '%s' was invalid JSON. "
                             "The log output contains more information."
                             % str(config_file))

        for opt in self.__dict__[_K_OPTIONS].values():
            # Do not let anything to happen with the current configuration
            # if there is a "schema mismatch" between what is in memory and
            # what keys exist in the file. The user MUST appropriately restart
            # the server in case a configuration option is added or removed
            # without an appropriate default= being set up in the Option()
            # constructor, as accesses to the value will result in exceptions
            # elsewhere.
            try:
                old = opt(current_cfg)
            except KeyError:
                LOG.error("Failed to load value of '%s' from the current "
                          "configuration, and this option does NOT have a "
                          "default. Please check and update your "
                          "configuration file, and restart! The server will "
                          "keep considering the value UNCONFIGURED!", opt.name)
                continue
            try:
                new = opt(new_cfg)
            except KeyError:
                LOG.error("Failed to load value of '%s' from the disk. "
                          "This option does NOT have a default. Please check "
                          "and update your configuration file, and restart! "
                          "The server will keep using the old value...",
                          opt.name)
                continue

            if old == new:
                # No change in the configured value, nothing to do.
                continue

            if not opt.is_dynamically_updatable:
                LOG.warning("Value of config option '%s' changed from "
                            "'%s' (in memory) to '%s' (in file), but this "
                            "option does not support on-the-fly reloading.",
                            opt.name, str(old), str(new))
                continue

            try:
                opt._update(current_cfg, new_cfg)
                LOG.info("Value of config option '%s' changed from "
                         "'%s' to '%s'.",
                         opt.name, str(old), str(new))
                updated_opts.append(opt.name)
            except Exception:
                LOG.warning("Failed to on-the-fly reload '%s'",
                            opt.name)
                import traceback
                traceback.print_exc()

        LOG.info("Done reloading configuration file '%s'", self.file_path)
        return updated_opts
