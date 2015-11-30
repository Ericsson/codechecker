/**
 * -------------------------------------------------------------------------
 *                     The CodeChecker Infrastructure
 *   This file is distributed under the University of Illinois Open Source
 *   License. See LICENSE.TXT for details.
 * -------------------------------------------------------------------------
 */

#include "ldlogger-tool.h"
#include "ldlogger-util.h"

#include <sys/types.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <ctype.h>

/**
 * States for GCCargument parser.
 */
typedef enum _GccArgsState
{
  /**
   * Normal state (default).
   */
  Normal,
  /**
   * After a -o paramater.
   */
  InOutputArg
} GccArgsState;

/**
 * List of file extensions accepted as source file.
 */
static const char* const srcExts[] = {
  "c", "cc", "cpp", "cxx", "h", "hh", "hxx", "hpp", "o", "so", "a", NULL
};

/**
 * Check if the given path is a gcc libpath or not.
 *
 * @param path_ an absolute directory path.
 * @return true if the given path is a gcc lib path, false if not.
 */
static int isGccLibPath(const char* path_)
{
  /* FIXME: it could be lib32 or lib64??? */
  const char* gccStart = strstr(path_, "/lib/gcc");
  if (!gccStart)
  {
    return 0;
  }

  /* We want to filter paths like:
   *   /usr/lib/gcc/x86_64-linux-gnu/4.8/include
   *   /usr/lib/gcc/x86_64-linux-gnu/4.8/include-fixed */
  return strstr(gccStart, "include") != NULL;
}

/**
 * Processes an command line argument for a GCC like command.
 *
 * @param state_ the current state of the parser.
 * @param arg_ the current command line argument.
 * @param action the current action.
 * @return the new state.
 */
static GccArgsState processArgument(
  GccArgsState state_,
  const char* arg_,
  LoggerAction* action_)
{
  char argToAdd[PATH_MAX];
  strcpy(argToAdd, arg_);

  if (state_ == InOutputArg)
  {
    if (!loggerMakePathAbs(arg_, argToAdd, 0))
    {
      strcpy(argToAdd, arg_);
    }

    loggerFileInitFromPath(&action_->output, argToAdd);
    state_ = Normal;
  }
  else if (strcmp(arg_, "-o") == 0)
  {
    state_ = InOutputArg;
  }
  else if (arg_[0] == '-' && (arg_[1] == 'I' || arg_[1] == 'L') && arg_[2])
  {
    /* This is a -I or -L option with a path */
    char fullPath[PATH_MAX];
    if (loggerMakePathAbs(arg_ + 2, fullPath, 0))
    {
      argToAdd[2] = 0;
      strcat(argToAdd, fullPath);
    }
  }
  else
  {
    char fullPath[PATH_MAX];
    if (loggerMakePathAbs(argToAdd, fullPath, 1))
    {
      char* ext = loggerGetFileExt(fullPath, 1);
      if (ext)
      {
        int i;
        for (i = 0; srcExts[i]; ++i)
        {
          if (strcmp(srcExts[i], ext) == 0)
          {
            strcpy(argToAdd, fullPath);
            loggerVectorAddUnique(&action_->sources,  loggerStrDup(fullPath),
              (LoggerCmpFuc) &strcmp);
            break;
          }
        }
      }

      free(ext);
    }
  }

  if (argToAdd[0])
  {
    loggerVectorAdd(&action_->arguments, loggerStrDup(argToAdd));
  }

  return state_;
}

/**
 * Tries to get the default header includes from a gcc(like) command and stores
 * the result into the given vector.
 *
 * @param prog_ the gcc like program / command.
 * @param args_ a vector for the arguments.
 */
static void getDefaultArguments(const char* prog_, LoggerVector* args_)
{
  char command[PATH_MAX];
  FILE* cmdOut;
  char* line = NULL;
  size_t lineSize = 0;
  ssize_t readSize;
  int incStarted = 0;

  strcpy(command, prog_);
  strcat(command, " -xc++ -E -v - < /dev/null 2>&1");

  cmdOut = popen(command, "r");
  if (!cmdOut)
  {
    return;
  }

  while ((readSize = getline(&line, &lineSize, cmdOut)) >= 0)
  {
    char fullPath[PATH_MAX] = "-I";
    char* pathEnd;
    char* pathStart;

    if (!incStarted)
    {
      if (strstr(line, "#include <...> search starts here"))
      {
        incStarted = 1;
      }
      continue;
    }
    else if (strstr(line, "End of search list"))
    {
      break;
    }

    /* Drop the new line character from the end of the line and the leading
       whitespaces. */
    for (pathStart = line; *pathStart && isspace(*pathStart); ++pathStart) {}
    for (pathEnd = pathStart; *pathEnd && !isspace(*pathEnd); ++pathEnd) {}
    *pathEnd = 0;
    if (pathStart[0] == 0)
    {
      /* WTF??? */
      continue;
    }

    if (!loggerMakePathAbs(pathStart, fullPath + 2, 0))
    {
      /* Invalid path, skip */
      continue;
    }

    if (isGccLibPath(fullPath))
    {
      /* We have to skip builtin gcc headers, we only need the paths to the
         stdlib */
      continue;
    }


    loggerVectorAdd(args_, loggerStrDup(fullPath));
  }

  free(line);
  pclose(cmdOut);
}

int loggerGccParserCollectActions(
  const char* prog_,
  const char* toolName_,
  const char* const argv_[],
  LoggerVector* actions_)
{
  size_t i;
  /* Position of the last include path + 1 */
  size_t lastIncPos = 1;
  GccArgsState state = Normal;
  LoggerAction* action = loggerActionNew(toolName_);

  loggerVectorAdd(&action->arguments, loggerStrDup(toolName_));

  for (i = 1; argv_[i]; ++i)
  {
    state = processArgument(state, argv_[i], action);
    if (argv_[i][0] == '-' && argv_[i][1] == 'I')
    {
      if (argv_[i][2])
      {
        /* -I with path argument */
        lastIncPos = action->arguments.size;
      }
      else
      {
        /* The path should be the next argument */
        lastIncPos = action->arguments.size + 1;
      }
    }
  }

  if (!getenv("CC_LOGGER_NO_DEF_DIRS"))
  {
    LoggerVector defIncludes;
    loggerVectorInit(&defIncludes);

    getDefaultArguments(prog_, &defIncludes);
    if (defIncludes.size)
    {
      loggerVectorAddFrom(&action->arguments, &defIncludes,
        &lastIncPos, (LoggerDupFuc) &loggerStrDup);
    }

    loggerVectorClear(&defIncludes);
  }

  /*
   * Workaround for -MT and friends: if the source set contains the output,
   * then we have to remove it from the set.
   */
  i = loggerVectorFind(&action->sources, action->output.path,
    (LoggerCmpFuc) &strcmp);
  if (i != SIZE_MAX)
  {
    loggerVectorErase(&action->sources, i);
  }

  loggerVectorAdd(actions_, action);
  return 1;
}
