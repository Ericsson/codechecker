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
#include <unistd.h>
#include <string.h>
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
 * List of file extensions accepted as object file.
 */
static const char* const objExts[] = {
  "o", "so", "a", NULL
};

/**
 * List of compiler name infixes belonging to C compilers.
 */
static const char* const cCompiler[] = {
  "gcc", "cc", "clang", NULL
};

/**
 * List of compiler name infixes belonging to C++ compilers.
 */
static const char* const cppCompiler[] = {
  "g++", "c++", "clang++", NULL
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
  else if (arg_[0] == '-' && ((arg_[1] == 'W' && (arg_[2] == 'l' || arg_[2] == 'p')) || arg_[1] == 'M'))
  {
    /* This is a -Wl linker option
     *  -Wl,-Map,output.map
     *  or a -Wp prepocessor option
     *  -Wp,option
     *  also matches for options like -Wpedantic
     *  handled here to skip for matching source files in
     *  these arguments
     */
    strcpy(argToAdd, arg_);
  }
  else if (arg_[0] == '-' && arg_[1] == 'D')
  {
    /*  Match for macro definition -D
     *  handled here to skip for matching source files in
     *  these arguments
     */
    strcpy(argToAdd, arg_);
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
  /* WARNING: this always gets the C++ compiler include
   * dirs even if we are compiling C file.
   * */
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

/**
 * This function inserts the paths from the given environment variable to the
 * vector.
 *
 * Implementation details: This function is used to fetch the value in any of
 * CPATH, C_INCLUDE_PATH, CPLUS_INCLUDE_PATH, OBJC_INCLUDE_PATH variables.
 * These contain paths separated by colon. An empty path means the current
 * working directory
 * (see https://gcc.gnu.org/onlinedocs/cpp/Environment-Variables.html).
 *
 * &param paths_ A vector in which the items from envVar_ are added.
 * @param envVar_ An environment variable which contains paths separated by
 * color (:) character. If no such environment variable is set then the vector
 * remains untouched.
 * @param flag_ A flag which is also inserted before each element in the vector
 * as another element (e.g. -I or -isystem). If this is a NULL pointer then
 * this flag will not be inserted in the vector.
 */
void getPathsFromEnvVar(
  LoggerVector* paths_,
  const char* envVar_,
  const char* flag_)
{
  char* env;

  env = getenv(envVar_);

  if (!env)
    return;

  const char* from = env;
  const char* to = strchr(env, ':');

  while (to)
  {
    char token[PATH_MAX];
    size_t length = to - from;
    strncpy(token, from, length);
    token[length] = 0;
    from = to + 1;
    to = strchr(from, ':');

    if (flag_)
      loggerVectorAdd(paths_, loggerStrDup(flag_));

    if (strcmp(token, "") == 0)
      loggerVectorAdd(paths_, loggerStrDup("."));
    else
      loggerVectorAdd(paths_, loggerStrDup(token));
  }

  loggerVectorAdd(paths_, loggerStrDup(flag_));
  if (*from == 0)
    loggerVectorAdd(paths_, loggerStrDup("."));
  else
    loggerVectorAdd(paths_, loggerStrDup(from));
}

char* findFullPath(const char* executable, char* fullpath) {
  char* path;
  char* dir;
  path = strdup(getenv("PATH"));
  for (dir = strtok(path, ":"); dir; dir = strtok(NULL, ":")) {
    strcpy(fullpath, dir);
    strcpy(fullpath + strlen(dir), "/");
    strcpy(fullpath + strlen(dir) + 1, executable);
    if (access(fullpath, F_OK ) != -1 ) {
        free(path);
        return fullpath;
    }
  }
  free(path);
  return 0;
}

int isObjectFile(const char* filename_)
{
  char* ext = loggerGetFileExt(filename_, 1);

  int i;
  for (i = 0; objExts[i]; ++i)
    if (strcmp(ext, objExts[i]) == 0)
    {
      free(ext);
      return 1;
    }

  free(ext);
  return 0;
}

int loggerGccParserCollectActions(
  const char* prog_,
  const char* toolName_,
  const char* const argv_[],
  LoggerVector* actions_)
{
  enum Language { C, CPP, OBJC } lang = CPP;

  size_t i;
  /* Position of the last include path + 1 */
  char full_prog_path[PATH_MAX+1];
  char *path_ptr;

  size_t lastIncPos = 1;
  size_t lastSysIncPos = 1;
  GccArgsState state = Normal;
  LoggerAction* action = loggerActionNew(toolName_);

  char* keepLinkVar = getenv("CC_LOGGER_KEEP_LINK");
  int keepLink = keepLinkVar && strcmp(keepLinkVar, "true") == 0;

  /* If prog_ is a relative path we try to
   * convert it to absolute path.
   */
  path_ptr = realpath(prog_, full_prog_path);

  /* If we cannot convert it, we try to find the
   * executable in the PATH.
   */
  if (!path_ptr)
	  path_ptr = findFullPath(toolName_, full_prog_path);
  if (path_ptr) /* Log compiler with full path. */
	  loggerVectorAdd(&action->arguments, loggerStrDup(full_prog_path));
  else  /* Compiler was not found in path, log the binary name only. */
  	  loggerVectorAdd(&action->arguments, loggerStrDup(toolName_));

  /* Determine programming language based on compiler name. */
  for (i = 0; cCompiler[i]; ++i)
    if (strstr(toolName_, cCompiler[i]))
      lang = C;

  for (i = 0; cppCompiler[i]; ++i)
    if (strstr(toolName_, cppCompiler[i]))
      lang = CPP;

  for (i = 1; argv_[i]; ++i)
  {
    const char* current = argv_[i];
    state = processArgument(state, current, action);

    if (current[0] == '-')
    {
      /* Determine the position of the last -I and -isystem flags.
       * Depending on whether the parameter of -I or -isystem is separated
       * from the flag by a space character.
       * 2 == strlen("-I") && 8 == strlen("-isystem")
       */
      if (current[1] == 'I')
        lastIncPos = action->arguments.size + (current[2] ? 0 : 1);
      else if (strstr(current, "-isystem") == current)
        lastSysIncPos = action->arguments.size + (current[8] ? 0 : 1);

      /* Determine the programming language based on -x flag.
       */
      else if (strcmp(current, "-x") == 0)
      {
        /* TODO: The language value after -x can be others too. See the man
         * page of GCC.
         * TODO: According to a GCC warning the -x flag has no effect when it
         * is placed after the last input file to be compiled.
         */
        const char* l = argv_[i + 1];
        if (strcmp(l, "c") == 0 || strcmp(l, "c-header") == 0)
          lang = C;
        else if (strcmp(l, "c++") == 0 || strcmp(l, "c++-header") == 0)
          lang = CPP;
      }
    }
  }

  if (getenv("CC_LOGGER_DEF_DIRS"))
  {
    LoggerVector defIncludes;
    loggerVectorInit(&defIncludes);

    getDefaultArguments(prog_, &defIncludes);
    if (defIncludes.size)
    {
      loggerVectorAddFrom(&action->arguments, &defIncludes,
        &lastIncPos, (LoggerDupFuc) &loggerStrDup);

      if (lastSysIncPos > lastIncPos)
        lastSysIncPos += defIncludes.size;

      lastIncPos += defIncludes.size;
    }

    loggerVectorClear(&defIncludes);
  }

  if (getenv("CPATH"))
  {
    LoggerVector includes;
    loggerVectorInit(&includes);

    getPathsFromEnvVar(&includes, "CPATH", "-I");
    if (includes.size)
    {
      loggerVectorAddFrom(&action->arguments, &includes,
        &lastIncPos, (LoggerDupFuc) &loggerStrDup);

      if (lastSysIncPos > lastIncPos)
        lastSysIncPos += includes.size;

      lastIncPos += includes.size;
    }

    loggerVectorClear(&includes);
  }

  if (lang == CPP && getenv("CPLUS_INCLUDE_PATH"))
  {
    LoggerVector includes;
    loggerVectorInit(&includes);

    getPathsFromEnvVar(&includes, "CPLUS_INCLUDE_PATH", "-isystem");
    if (includes.size)
    {
      loggerVectorAddFrom(&action->arguments, &includes,
        &lastSysIncPos, (LoggerDupFuc) &loggerStrDup);
    }

    loggerVectorClear(&includes);
  }
  else if (lang == C && getenv("C_INCLUDE_PATH"))
  {
    LoggerVector includes;
    loggerVectorInit(&includes);

    getPathsFromEnvVar(&includes, "C_INCLUDE_PATH", "-isystem");
    if (includes.size)
    {
      loggerVectorAddFrom(&action->arguments, &includes,
        &lastSysIncPos, (LoggerDupFuc) &loggerStrDup);
    }

    loggerVectorClear(&includes);
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

  if (!keepLink)
    do {
      i = loggerVectorFindIf(&action->sources, (LoggerPredFuc) &isObjectFile);
      loggerVectorErase(&action->sources, i);
    } while (i != SIZE_MAX);

  if (action->sources.size != 0)
    loggerVectorAdd(actions_, action);

  return 1;
}
