# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Handles the retrieval and access to the file-based configuration of a server.
"""
from datetime import timedelta
import os
from pathlib import Path
import shutil
import stat
from typing import cast

from codechecker_common.configuration_access import Configuration, Schema, \
    OptionDirectory, OptionDirectoryList
from codechecker_common.logger import get_logger

from codechecker_web.shared.env import check_file_owner_rw


LOG = get_logger("server")


def register_configuration_options(s: Schema) -> Schema:
    """
    Registers the `Schema` of `Option`s that are accessible in a server
    configuration file.

    Returns the `Schema` object.
    """
    s.add_option("max_run_count", "./max_run_count",
                 default=None,
                 validation_predicate=lambda v:
                 v is None or isinstance(v, int),
                 validation_fail_action="A size limit must be a number.",
                 # FIXME: Obnoxious design, but changing this would break
                 # reverse compatibility against currently configured
                 # deployments.
                 description="The maximum storable run count. If 'None' or "
                             "negative, an unlimited amount can be stored."
                 )

    s.add_option("worker_processes", "./worker_processes",
                 default=os.cpu_count(),
                 validation_predicate=lambda v: isinstance(v, int) and v > 0,
                 validation_fail_action="The number of 'worker_processes' "
                                        "can not be 0 or negative!",
                 read_only=True,
                 supports_update=False,
                 description="The number of API request handler processes "
                             "to start on the server."
                 )

    store = cast(OptionDirectory,
                 s.add_option("store", "./store/",
                              description="Configuration for the handling of "
                                          "'store' endpoint operations."
                              ))

    store.add_option("analysis_statistics_dir",
                     "./analysis_statistics_dir",
                     default=None,
                     validation_predicate=lambda v: v is None or (
                         isinstance(v, str) and bool(v)),
                     description="The server-side directory where compressed "
                                 "analysis statistics files should be saved. "
                                 "If unset (None), analysis statistics are "
                                 "NOT stored on the server."
                     )

    store_limits = cast(OptionDirectory,
                        store.add_option("store_limits", "./limit/",
                                         description="Allowed size and time "
                                                     "limits during a "
                                                     "'store'."
                                         ))

    store_limits.add_option("failure_zip_size",
                            "./failure_zip_size",
                            default=50 * 1024 * 1024,  # 50 MiB.
                            validation_predicate=lambda v:
                            v is None or (isinstance(v, int) and v >= 0),
                            validation_fail_action="A size limit can not be "
                                                   "negative.",
                            read_only=False,
                            description="The maximum size of the collected "
                                        "failure ZIPs which can be stored on "
                                        "the server."
                            )

    store_limits.add_option("compilation_database_size",
                            "./compilation_database_size",
                            default=100 * 1024 * 1024,  # 100 MiB.
                            validation_predicate=lambda v:
                            v is None or (isinstance(v, int) and v >= 0),
                            validation_fail_action="A size limit can not be "
                                                   "negative.",
                            read_only=False,
                            description="The limit for the compilation "
                                        "database file size."
                            )

    keepalive = cast(OptionDirectory,
                     s.add_option("keepalive", "/keepalive/",
                                  description="TCP keep-alive configuration "
                                              "parameters for the server's "
                                              "listen socket."
                                  ))

    keepalive.add_option("enable_keepalive", "./enabled",
                         default=False,
                         supports_update=False,
                         description="Whether to set up TCP keep-alive on "
                                     "the server socket. This is recommended "
                                     "to be turned on in a distributed "
                                     "environment, such as Docker Swarm."
                         )

    keepalive.add_option("keepalive_time_idle",
                         "./idle",
                         default=None,
                         validation_predicate=lambda v:
                         v is None or (isinstance(v, int) and v >= 0),
                         validation_fail_action="A time limit can not be "
                                                "negative.",
                         read_only=False,
                         supports_update=False,
                         description="The interval (in seconds) after the "
                                     "sending of the last data packet "
                                     "(excluding ACKs) and the first "
                                     "keepalive probe. If unset (None), the "
                                     "default will be taken from the system "
                                     "configuration "
                                     "'net.ipv4.tcp_keepalive_time'."
                         )

    keepalive.add_option("keepalive_time_interval",
                         "./interval",
                         default=None,
                         validation_predicate=lambda v:
                         v is None or (isinstance(v, int) and v >= 0),
                         validation_fail_action="A time limit can not be "
                                                "negative.",
                         read_only=False,
                         supports_update=False,
                         description="The interval (in seconds) between the "
                                     "sending of subsequent keepalive probes."
                                     "If unset (None), the default will be "
                                     "taken from the system configuration "
                                     "'net.ipv4.tcp_keepalive_intvl'."
                         )

    keepalive.add_option("keepalive_max_probes",
                         "./max_probe",
                         default=None,
                         validation_predicate=lambda v:
                         v is None or (isinstance(v, int) and v >= 0),
                         validation_fail_action="A size limit can not be "
                                                "negative.",
                         read_only=False,
                         supports_update=False,
                         description="The number of unacknowledged keepalive "
                                     "probes to send before the connection "
                                     "is considered dead by the kernel, and "
                                     "this is signalled to the server "
                                     "process. If unset (None), the default "
                                     "will be taken from the system "
                                     "configuration "
                                     "'net.ipv4.tcp_keepalive_probes'."
                         )

    auth = cast(OptionDirectory,
                s.add_option("authentication", "./authentication/",
                             description="Authentication (privilege-only "
                                         "access) configuration root."
                             ))

    auth.add_option("auth_enabled", "./enabled",
                    default=False,
                    validation_predicate=lambda v: isinstance(v, bool),
                    read_only=False,
                    supports_update=False,
                    description="Toggles the entire authentication system."
                    )

    auth.add_option("auth_logins_until_cleanup", "./logins_until_cleanup",
                    default=60,
                    validation_predicate=lambda v: isinstance(v, int)
                    and v >= 0,
                    validation_fail_action="A counter limit can not be "
                                           "negative.",
                    description="After this many login attempts, the server "
                                "should perform an automatic cleanup of old, "
                                "expired sessions."
                    )

    auth.add_option("auth_session_lifetime", "./session_lifetime",
                    default=int(timedelta(minutes=5).total_seconds()),
                    validation_predicate=lambda v: isinstance(v, int)
                    and v > 0,
                    validation_fail_action="A time limit can not be negative.",
                    description="If an authenticated session is not accessed "
                                "for this many seconds, it will be "
                                "permanently invalidated, and the user "
                                "logged out."
                    )

    auth.add_option("auth_refresh_time", "./refresh_time",
                    default=int(timedelta(minutes=1).total_seconds()),
                    validation_predicate=lambda v: isinstance(v, int)
                    and v > 0,
                    validation_fail_action="A time limit can not be negative.",
                    description="If an authenticated session is not accessed "
                                "for this many seconds, it will be validated "
                                "against the contents of the database as "
                                "opposed to reusing the local (in-memory) "
                                "cache."
                    )

    auth_regex_groups = cast(OptionDirectory,
                             auth.add_option(
                                 "auth_regex_groups", "./regex_groups/",
                                 description="Allows creating virtual "
                                             "groups usable by other "
                                             "subsystems based on username "
                                             "patterns matching regular "
                                             "expressions."
                             ))

    auth_regex_groups.add_option("auth_regex_groups_enabled", "./enabled",
                                 default=False,
                                 validation_predicate=lambda v:
                                 isinstance(v, bool),
                                 read_only=False,
                                 supports_update=False,
                                 description="Toggles this authentication "
                                             "subsystem."
                                 )

    auth_regex_groups.add_option("auth_regex_groups_groups", "./groups",
                                 default={},
                                 secret=True,
                                 validation_predicate=lambda v:
                                 isinstance(v, dict) and
                                 all(isinstance(v2, list)
                                     for v2 in v.values()),
                                 supports_update=False,
                                 description="Mapping of virtual group names "
                                             "to a list of username patterns."
                                 )

    dictionary_auth = cast(OptionDirectory,
                           auth.add_option(
                               "dictionary_auth", "./method_dictionary/",
                               description="Hardcoded dicitonary based "
                                           "authentication."
                           ))

    dictionary_auth.add_option("dictionary_auth_enabled", "./enabled",
                               default=False,
                               validation_predicate=lambda v:
                               isinstance(v, bool),
                               supports_update=False,
                               description="Toggles this authentication "
                                           "subsystem."
                               )

    dictionary_auth.add_option("dictionary_auth_auths", "./auths",
                               default=[],
                               secret=True,
                               validation_predicate=lambda v:
                               isinstance(v, list),
                               supports_update=False,
                               description="'Username:Password' of the known "
                                           "and allowed users."
                               )

    dictionary_auth.add_option("dictionary_auth_groups", "./groups",
                               default={},
                               secret=True,
                               validation_predicate=lambda v:
                               isinstance(v, dict) and
                               all(isinstance(v2, list) for v2 in v.values()),
                               supports_update=False,
                               description="Mapping of user names to the "
                                           "authentication groups they "
                                           "belong to."
                               )

    pam_auth = cast(OptionDirectory,
                    auth.add_option("pam_auth", "./method_pam/",
                                    description="Linux PAM based "
                                                "authentication."
                                    ))

    pam_auth.add_option("pam_auth_enabled", "./enabled",
                        default=False,
                        validation_predicate=lambda v:
                        isinstance(v, bool),
                        read_only=False,
                        supports_update=False,
                        description="Toggles this authentication subsystem."
                        )

    pam_auth.add_option("pam_auth_auths", "./users",
                        default=[],
                        secret=True,
                        validation_predicate=lambda v:
                        isinstance(v, list),
                        supports_update=False,
                        description="The list of PAM user names allowed to "
                                    "access the system."
                        )

    pam_auth.add_option("pam_auth_groups", "./groups",
                        default=[],
                        secret=True,
                        validation_predicate=lambda v:
                        isinstance(v, list),
                        supports_update=False,
                        description="The list of PAM group names allowed to "
                                    "access the system."
                        )

    ldap_auth = cast(OptionDirectory,
                     auth.add_option("ldap_auth", "./method_ldap/",
                                     description="LDAP-based authentication."
                                     ))

    ldap_auth.add_option("ldap_auth_enabled", "./enabled",
                         default=False,
                         validation_predicate=lambda v:
                         isinstance(v, bool),
                         read_only=False,
                         supports_update=False,
                         description="Toggles this authentication subsystem."
                         )

    ldap_authorities = cast(OptionDirectoryList,
                            ldap_auth.add_option(
                                "ldap_authorities", "./authorities[]/",
                                description="A priority list of LDAP "
                                            "authority servers where the "
                                            "users' authentication requests "
                                            "will be validated against."
                            ))

    ldap_authorities.add_option("ldap_connection_url", "./connection_url",
                                supports_update=False,
                                validation_predicate=lambda v:
                                v is None or isinstance(v, str),
                                description="URL of the LDAP server which "
                                            "will be queried for user "
                                            "information and group "
                                            "membership."
                                )

    ldap_authorities.add_option("ldap_tls_require_cert", "./tls_require_cert",
                                default="always",
                                validation_predicate=lambda v:
                                v in ["always", "never"],
                                supports_update=False,
                                description="If set to 'never', skip "
                                            "certificate verification during "
                                            "'ldaps://' connections. "
                                            "Using this option is insecure!"
                                )

    ldap_authorities.add_option("ldap_username", "./username",
                                default=None,
                                secret=True,
                                validation_predicate=lambda v:
                                v is None or isinstance(v, str),
                                supports_update=False,
                                description="Username for the LDAP bind() "
                                            "call used for the server "
                                            "connection. "
                                            "If unset, the to-be logged-in "
                                            "user's username is used."
                                )

    ldap_authorities.add_option("ldap_password", "./password",
                                default=None,
                                secret=True,
                                supports_update=False,
                                validation_predicate=lambda v:
                                v is None or isinstance(v, str),
                                description="Password for the LDAP bind() "
                                            "call used for the server "
                                            "connection. "
                                            "If unset, the to-be logged-in "
                                            "user's credentials are used."
                                )

    ldap_authorities.add_option("ldap_use_referrals", "./referrals",
                                default=False,
                                supports_update=False,
                                validation_predicate=lambda v:
                                isinstance(v, bool),
                                description="Microsoft AD by default returns "
                                            "referral (search continuation) "
                                            "objects, which do not synergise "
                                            "well with 'libldap', as it is "
                                            "not specified what credentials "
                                            "should be used to follow up on "
                                            "the referral. "
                                            "Because of this, and because "
                                            "the default (anonymous) "
                                            "behaviour might fail, using "
                                            "referrals is opt-in."
                                )

    ldap_authorities.add_option("ldap_deref", "./deref",
                                default="always",
                                supports_update=False,
                                validation_predicate=lambda v:
                                v in ["always", "never"],
                                description="Configure how the alias "
                                            "dereferencing is done in "
                                            "'libldap'."
                                )

    ldap_authorities.add_option("ldap_account_base", "./accountBase",
                                default=None,
                                supports_update=False,
                                validation_predicate=lambda v:
                                v is None or isinstance(v, str),
                                description="Root tree containing all "
                                            "user accounts."
                                )

    ldap_authorities.add_option("ldap_account_scope", "./accountScope",
                                default="subtree",
                                supports_update=False,
                                validation_predicate=lambda v:
                                v in ["base", "one", "subtree"],
                                description="Scope of the search performed."
                                )

    ldap_authorities.add_option("ldap_account_pattern", "./accountPattern",
                                default=None,
                                supports_update=False,
                                validation_predicate=lambda v:
                                v is None or isinstance(v, str),
                                description="Query pattern used to search "
                                            "for a user account. "
                                            "Must be an LDAP query "
                                            "expression, and the special "
                                            "$USN$ token is replace with the "
                                            "username of the to-be logged-in "
                                            "user."
                                )

    ldap_authorities.add_option("ldap_userDN_postfix_preference",
                                "./user_dn_postfix_preference",
                                default=None,
                                supports_update=False,
                                validation_predicate=lambda v:
                                v is None or isinstance(v, str),
                                description="Used to select the preferred "
                                            "user DN if multiple entries are "
                                            "returned by the LDAP search. "
                                            "The configured value will be "
                                            "matched and the first matching "
                                            "user DN is used, in case "
                                            "multiple choices were "
                                            "available. "
                                            "If unset and multiple choices "
                                            "had been available, the first "
                                            "result is used, which may be "
                                            "non-deterministic!"
                                )

    ldap_authorities.add_option("ldap_group_base", "./groupBase",
                                default=None,
                                supports_update=False,
                                validation_predicate=lambda v:
                                v is None or isinstance(v, str),
                                description="Root tree containing all groups."
                                )

    ldap_authorities.add_option("ldap_group_scope", "./groupScope",
                                default="subtree",
                                supports_update=False,
                                validation_predicate=lambda v:
                                v in ["base", "one", "subtree"],
                                description="Scope of the search performed."
                                )

    ldap_authorities.add_option("ldap_group_pattern", "./groupPattern",
                                default=None,
                                supports_update=False,
                                validation_predicate=lambda v:
                                v is None or isinstance(v, str),
                                description="Query pattern used to search "
                                            "for the group(s) of a user. "
                                            "Must be an LDAP query "
                                            "expression, and the special "
                                            "$USERDN$ token is replace with "
                                            "the obtained user DN for to-be "
                                            "logged-in user."
                                )

    ldap_authorities.add_option("ldap_group_name_attribute", "./groupNameAttr",
                                default=None,
                                supports_update=False,
                                validation_predicate=lambda v:
                                v is None or isinstance(v, str),
                                description="The attribute of the GROUP "
                                            "object which contains the name "
                                            "of the group."
                                )

    return s


def get_example_configuration_file_path() -> Path:
    """
    Returns the location of the example configuration that is shipped
    together with the CodeChecker package.
    """
    return Path(os.environ["CC_DATA_FILES_DIR"],
                "config", "server_config.json")


def migrate_session_config_to_server_config(session_config_file: Path,
                                            server_config_file: Path) -> Path:
    """
    Migrates an existing, deprecated `session_config` file to its new
    `server_config` structure.

    Returns `server_config_file` path.
    """
    if session_config_file.exists() and not server_config_file.exists():
        LOG.warning("The use of '%s' file is deprecated since "
                    "CodeChecker v6.5!", session_config_file)

        session_config_file.rename(server_config_file)
        LOG.info("Automatically renamed '%s' to '%s'...\n\t"
                 "Please check the example configuration configuration file "
                 "('%s') or the User Guide "
                 "(http://codechecker.readthedocs.io) for more information.",
                 session_config_file, server_config_file,
                 get_example_configuration_file_path())
    return server_config_file


def create_server_config_file(server_config_file: Path) -> Path:
    """
    Creates a default server configuration file at the specified location from
    the package's built-in example.

    Returns `server_config_file` path.
    """
    if not server_config_file.exists():
        shutil.copy(get_example_configuration_file_path(), server_config_file)
        server_config_file.chmod(stat.S_IRUSR | stat.S_IWUSR)
        LOG.info("CodeChecker server's example configuration file created "
                 "at '%s'", server_config_file)
    return server_config_file


def load_configuration(config_directory: Path) -> Configuration:
    """
    Do whatever is needed to get to a valid server configuration at the
    expected file path under `config_directory`.
    Following that, read it, parse it, and return the contents as a
    schema-enabled `Configuration` object.
    """
    server_config = config_directory / "server_config.json"
    if not server_config.exists():
        server_config = migrate_session_config_to_server_config(
            config_directory / "session_config.json",
            server_config)
    if not server_config.exists():
        server_config = create_server_config_file(server_config)
    if not server_config.exists():
        LOG.fatal("Server configuration factory ran out of options to "
                  "instantiate a viable configuration for this instance!")
        raise FileNotFoundError(str(server_config))

    # This helper function prints a warning to the output if the access
    # to the file is too permissive.
    check_file_owner_rw(server_config)

    return Configuration.from_file(register_configuration_options(Schema()),
                                   server_config)
