/**
 * -------------------------------------------------------------------------
 *                     The CodeChecker Infrastructure
 *   This file is distributed under the University of Illinois Open Source
 *   License. See LICENSE.TXT for details.
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
#include <stdbool.h>

#include "ldlogger-hooks.h"

#define CC_LOGGER_MAX_ARGS 2048

#define CC_LOGGER_CALL_EXEC(funName_, arglist, ...) \
  tryLog(__VA_ARGS__); \
  { \
    unsetLDPRELOAD(__VA_ARGS__); \
    typedef int (*FunType) arglist; \
    FunType fun = (FunType) dlsym(RTLD_NEXT, #funName_); \
    if (!fun) \
    { \
      return -1; \
    } \
    return (*fun)( __VA_ARGS__ ); \
  }

static void unsetLDPRELOAD(const char* const filename_, ...)
{
  char ldd[] = "ldd";
  const char* pos = strstr(filename_, ldd);
  if (pos)
  {
    unsigned int pos_number = pos-filename_;
    unsigned int prefix_length = strlen(filename_)-strlen(ldd);
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
 * @param filename_ the filename / command (see lookupPath_).
 * @param argv_ arguments.
 */
static void tryLog(
  const char* const filename_,
  char* const argv_[], ...)
{
  size_t i;
  const char* loggerArgs[CC_LOGGER_MAX_ARGS];
  char* ldpreload;

  loggerArgs[0] = filename_;
  for (i = 0; argv_[i]; ++i)
  {
    loggerArgs[i+1] = argv_[i];
  }
  loggerArgs[i+1] = NULL;

  logExec(i+1, (char* const*) loggerArgs);
}

__attribute__ ((visibility ("default"))) int execv(const char* filename_, char* const argv_[])
{
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
