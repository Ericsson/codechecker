/**
 * -------------------------------------------------------------------------
 *  Part of the CodeChecker project, under the Apache License v2.0 with
 *  LLVM Exceptions. See LICENSE for license information.
 *  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
 * -------------------------------------------------------------------------
 */

#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif

#include <dlfcn.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#include <spawn.h>
#include <stdbool.h>

#include "ldlogger-hooks.h"

// We are done intercepting system calls by pretending that the functions below
// are the real thing -- time to call the actual system call.
#define CALL_ORIGINAL_FN(funName_, arglist, ...) \
  typedef int (*FunType) arglist; \
  FunType fun = (FunType) dlsym(RTLD_NEXT, #funName_); \
  if (!fun) \
  { \
    return -1; \
  } \
  return (*fun)( __VA_ARGS__ );

#define CC_LOGGER_CALL_EXEC(funName_, arglist, ...) \
  tryLog(__VA_ARGS__); \
  { \
    unsetLDPRELOAD(__VA_ARGS__); \
    CALL_ORIGINAL_FN(funName_, arglist, __VA_ARGS__) \
  }

#define CC_LOGGER_CALL_POSIX_SPAWN(funName_)                                   \
  /*                                                                           \
    The first arg of posix_spawn (unlike the exec* calls) is not the path to   \
    the program to execute, so we're not reusing CC_LOGGER_CALL_EXEC.          \
  */                                                                           \
  tryLog(path, argv);                                                          \
  CALL_ORIGINAL_FN(funName_,                                                   \
                   (pid_t *restrict, const char *restrict,                     \
                    const posix_spawn_file_actions_t *restrict,                \
                    const posix_spawnattr_t *restrict, char *const[restrict],  \
                    char *const[restrict]),                                    \
                   pid, path, file_actions, attrp, argv, envp)

// FIXME: What does this function do? Does it do anything? Does it *need* to do
// the thing we are not sure it does?
static void unsetLDPRELOAD(const char* const filename_, ...)
{
  char ldd[] = "ldd";
  const char* pos = strstr(filename_, ldd);
  if (pos)
  {
    unsigned int pos_number = pos-filename_;
    unsigned int prefix_length = strlen(filename_)-strlen(ldd);
    // FIXME: Why should we care? Is that bad?
    /* is there /ldd suffix in filename? or is filename equal ldd? */
    if ((prefix_length == pos_number) && ( pos_number == 0 || (pos-1 && *--pos == '/')))
    {
      unsetenv("LD_PRELOAD");
    }
  }
}

/**
 * Tries to log an exec* call.
 *
 * @param origin_ the exec* function name.
 * FIXME: lookupPath_ is not a thing in the entire CodeChecker repo, neither is
 * it in its entire git history.
 * @param filename_ the filename / command (see lookupPath_).
 * @param argv_ arguments.
 */
static void tryLog(
  const char* const filename_,
  char* const argv_[], ...)
{
  size_t i,argCount;
  const char** loggerArgs;

  for (i = 0,argCount = 0; argv_[i]; ++i)
  {
    argCount++;
  }

  loggerArgs = (const char **) malloc(sizeof(char*) * (argCount + 2));

  loggerArgs[0] = filename_;
  for (i = 0; argv_[i]; ++i)
  {
    loggerArgs[i+1] = argv_[i];
  }
  loggerArgs[i+1] = NULL;

  logExec(i+1, loggerArgs);

  free(loggerArgs);
}

__attribute__((visibility("default"))) int
posix_spawn(pid_t *restrict pid, const char *restrict path,
            const posix_spawn_file_actions_t *restrict file_actions,
            const posix_spawnattr_t *restrict attrp, char *const argv[restrict],
            char *const envp[restrict]) {
  CC_LOGGER_CALL_POSIX_SPAWN(posix_spawn)
}

__attribute__((visibility("default"))) int
posix_spawnp(pid_t *restrict pid, const char *restrict path,
             const posix_spawn_file_actions_t *restrict file_actions,
             const posix_spawnattr_t *restrict attrp,
             char *const argv[restrict], char *const envp[restrict]) {
  CC_LOGGER_CALL_POSIX_SPAWN(posix_spawnp)
}

__attribute__((visibility("default"))) int execv(const char *filename_,
                                                 char *const argv_[]) {
  CC_LOGGER_CALL_EXEC(execv, (const char*, char* const*),
    filename_, argv_);
}

__attribute__ ((visibility ("default"))) int execve(const char* filename_, char* const argv_[], char* const envp_[])
{
  CC_LOGGER_CALL_EXEC(execve, (const char*, char* const*, char* const*),
    filename_, argv_, envp_);
}

__attribute__ ((visibility ("default"))) int execvp(const char* filename_, char* const argv_[])
{
  CC_LOGGER_CALL_EXEC(execvp, (const char*, char* const*),
    filename_, argv_);
}

#ifdef _GNU_SOURCE
__attribute__ ((visibility ("default"))) int execvpe(const char* filename_, char *const argv_[], char* const envp_[])
{
  CC_LOGGER_CALL_EXEC(execvpe, (const char*, char* const*, char* const*),
    filename_, argv_, envp_);
}
#endif
