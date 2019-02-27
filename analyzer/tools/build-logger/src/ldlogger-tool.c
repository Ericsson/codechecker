/**
 * -------------------------------------------------------------------------
 *                     The CodeChecker Infrastructure
 *   This file is distributed under the University of Illinois Open Source
 *   License. See LICENSE.TXT for details.
 * -------------------------------------------------------------------------
 */

#include "ldlogger-tool.h"

#include <stdlib.h>
#include <assert.h>

#define PROG_LIST_SEPARATOR ":"

extern char** environ;

/**
 * Reads a colon separated list from the given environment variable and tries
 * to match to the given program name. If one program matches (from the list)
 * to the given program name, then it will return a non zero value.
 *
 * On any error or mismatch the function returns 0.
 *
 * @param envVar_ the name of environment variable.
 * @param progName_ program name to match.
 * @return non zero on match, 0 otherwise
 */
static int matchToProgramList(
  const char* envVar_,
  const char* progName_)
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
    if (strstr(progName_, token))
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

LoggerAction* loggerActionNew(char const* toolName_)
{
  LoggerAction* act = (LoggerAction*) malloc(sizeof(LoggerAction));
  if (!act)
  {
    return NULL;
  }

  loggerFileInitFromPath(&act->output, "./_noobj");
  loggerVectorInit(&act->arguments);
  loggerVectorInit(&act->sources);
  strcpy(act->toolName, toolName_);

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
  const char* toolName = strrchr(prog_, '/');
  if (toolName)
  {
    /* It was a path -> now its a program name */
    ++toolName;
  }
  else
  {
    /* Its a program name */
    toolName = prog_;
  }

  if (matchToProgramList("CC_LOGGER_GCC_LIKE", toolName))
  {
    int ret;
    turnLogging(0);
    ret = loggerGccParserCollectActions(prog_, toolName, argv_, actions_);
    turnLogging(1);
    return ret;
  }
  else if (matchToProgramList("CC_LOGGER_JAVAC_LIKE", toolName))
  {
    return loggerJavacParserCollectActions(prog_, toolName, argv_, actions_);
  }

  return 0;
}
