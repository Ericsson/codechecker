/**
 * -------------------------------------------------------------------------
 *  Part of the CodeChecker project, under the Apache License v2.0 with
 *  LLVM Exceptions. See LICENSE for license information.
 *  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
 * -------------------------------------------------------------------------
 */

#include "ldlogger-tool.h"
#include "ldlogger-util.h"

#include <stdlib.h>
#include <assert.h>
#include <string.h>

#define PROG_LIST_SEPARATOR ":"

extern char** environ;

/**
 * Reads a colon separated list from the given environment variable and tries
 * to match to the given program name. If one program matches (from the list)
 * to the given program name, then it will return a non zero value.
 *
 * If a (PROG_LIST_SEPARATOR separated) member of the envVar_ contains a slash
 * character then we assume that this is a postfix of a compiler's path.
 * Otherwise we assume that this is an infix of a compier's name.
 *
 * On any error or mismatch the function returns 0.
 *
 * @param envVar_ the name of environment variable.
 * @param progPath_ program path to match.
 * @return non zero on match, 0 otherwise
 */
static int matchToProgramList(
  const char* envVar_,
  const char* progPath_)
{
  char* progList;
  char* token;
  const char* progListVar = getenv(envVar_);
  if (!progListVar)
  {
    return 0;
  }

  progList = loggerStrDup(progListVar);
  if (!progList)
  {
    return 0;
  }

  token = strtok(progList, PROG_LIST_SEPARATOR);
  while (token)
  {
    int found = 0;

    if (strchr(token, '/'))
    {
      const char* posOfToken = strstr(progPath_, token);
      if (posOfToken)
        found = strcmp(posOfToken, token) == 0;
    }
    else
    {
      const char* progName = strrchr(progPath_, '/');

      if (progName)
        ++progName;
      else
        progName = progPath_;

      found = strstr(progName, token) != NULL;
    }

    if (found)
    {
      /* Match! */
      free(progList);
      return 1;
    }

    token = strtok(NULL, PROG_LIST_SEPARATOR);
  }

  free(progList);
  return 0;
}

/**
 *  Disable / enable recursive logging.
 */
static void turnLogging(int on)
{
  int i;
  for (i = 0; environ[i]; ++i)
  {
    if (strstr(environ[i], "LD_PRELOAD="))
    {
       environ[i][0] = on ? 'L' : 'X';
    }
  }
}

LoggerFile* loggerFileInitFromPath(LoggerFile* file_, const char* path_)
{
  assert(file_ && "file_ must be not NULL!");

  if (!loggerMakePathAbs(path_, file_->path, 0))
  {
    /* fallback to the given path */
    strcpy(file_->path, path_);
  }

  return file_;
}

LoggerAction* loggerActionNew()
{
  LoggerAction* act = (LoggerAction*) malloc(sizeof(LoggerAction));
  if (!act)
  {
    return NULL;
  }

  loggerFileInitFromPath(&act->output, "./_noobj");
  loggerVectorInit(&act->arguments);
  loggerVectorInit(&act->sources);

  return act;
}

void loggerActionFree(LoggerAction* act_)
{
  if (!act_)
  {
    return;
  }

  loggerVectorClear(&act_->arguments);
  loggerVectorClear(&act_->sources);
  free(act_);
}

int loggerCollectActionsByProgName(
  const char* prog_,
  const char* const argv_[],
  LoggerVector* actions_)
{
  if (matchToProgramList("CC_LOGGER_GCC_LIKE", prog_))
  {
    int ret;
    turnLogging(0);
    ret = loggerGccParserCollectActions(prog_, argv_, actions_);
    turnLogging(1);
    return ret;
  }
  else if (matchToProgramList("CC_LOGGER_JAVAC_LIKE", prog_))
  {
    return loggerJavacParserCollectActions(prog_, argv_, actions_);
  } else {
    const char* gccLike = getenv("CC_LOGGER_GCC_LIKE");
    const char* javacLike = getenv("CC_LOGGER_JAVAC_LIKE");

    LOG_INFO("'%s' does not match any program name! Current environment "
             "variables are: CC_LOGGER_GCC_LIKE (%s), "
             "CC_LOGGER_JAVAC_LIKE(%s)",
             prog_,
             gccLike ? gccLike : "",
             javacLike ? javacLike : "");
  }

  return 0;
}
