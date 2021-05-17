/**
 * -------------------------------------------------------------------------
 *  Part of the CodeChecker project, under the Apache License v2.0 with
 *  LLVM Exceptions. See LICENSE for license information.
 *  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
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
 * List of file extensions accepted as source file. Binaries can also be
 * sources of linker actions.
 */
static const char* const srcExts[] = {
  "c", "cc", "cp", "cpp", "cxx", "c++", "o", "so", "a", NULL
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
 * @param paths_ A vector in which the items from envVar_ are added.
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
    if (length > PATH_MAX - 1){
      // If the string is too long, skip it.
      from = to + 1;
      to = strchr(from, ':');
      continue;
    }
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

/**
 * Compilers (clang) support passing extra flags using so-called response
 * files that you specify with the @file syntax.
 * This function returns the response file path if it can be found in the
 * given arguments or NULL if is doesn't.
 * The returned string has to be deallocated by the caller.
 */
char* getResponseFile(const LoggerVector* arguments_)
{
  size_t i;

  for (i = 0; i < arguments_->size; ++i)
  {
    const char* arg = arguments_->data[i];
    if (arg != NULL && arg[0] == '@')
      return loggerStrDup(arg);
  }

  return NULL;
}

void transformSomePathsAbsolute(LoggerVector* args_)
{
  /* TODO: The argument of -I, -idirafter, -isystem and -iquote may
   * start with = sign which means that the following path is relative to
   * --sysroot (see: man gcc). This logic is not implemented here. */

  static const char* const absFlags[] = {
    "-I", "-idirafter", "-imultilib", "-iquote", "-isysroot", "-isystem",
    "-iwithprefix", "-iwithprefixbefore", "-sysroot", "--sysroot", NULL};

  int pathComing = 0;

  for (size_t i = 0; i < args_->size; ++i)
  {
    if (pathComing)
    {
      char newPath[PATH_MAX];
      loggerMakePathAbs(args_->data[i], newPath, 0);
      loggerVectorReplace(args_, i, loggerStrDup(newPath));
      pathComing = 0;
    }
    else
    {
      const char* const* flag;

      for (flag = absFlags;
          *flag && !startsWith(args_->data[i], *flag);
          ++flag)
        ;

      if (!*flag)
        continue;

      const char* path = (const char*)args_->data[i] + strlen(*flag);
      if (*path)
      {
        char newPath[PATH_MAX];
        strcpy(newPath, *flag);

        int hasEqual = *path == '=';
        if (hasEqual)
        {
          strcat(newPath, "=");
          ++path;
        }

        loggerMakePathAbs(path, newPath + strlen(*flag) + hasEqual, 0);
        loggerVectorReplace(args_, i, loggerStrDup(newPath));
      }
      else
        pathComing = 1;
    }
  }
}

int loggerGccParserCollectActions(
  const char* prog_,
  const char* const argv_[],
  LoggerVector* actions_)
{
  enum Language { C, CPP, OBJC } lang = CPP;

  size_t i;
  /* Position of the last include path + 1 */
  char full_prog_path[PATH_MAX+1];
  char *path_ptr = NULL;
  char* responseFile = NULL;

  size_t lastIncPos = 1;
  size_t lastSysIncPos = 1;
  LoggerAction* action = loggerActionNew();

  char* keepLinkVar = getenv("CC_LOGGER_KEEP_LINK");
  int keepLink = keepLinkVar && strcmp(keepLinkVar, "true") == 0;

  const char* toolName = strrchr(prog_, '/');
  if (toolName)
    ++toolName;
  else
    toolName = prog_;

  /* If prog_ is not an absolute path, we try to find it as an
   * executable in the PATH.
   * Earlier there was an approach to use realpath() in order to fetch
   * the absolute path of the binary. However, realpath() resolves the
   * symlinks in the path and it is not good for us.
   * The build environment can be set so "g++" is a symlink to
   * /usr/bin/ccache. CCache can detect whether it was run through this
   * symlink or it was run directly. In the former case CCache forwards
   * the command line arguments to the original g++ compiler. This way
   * we can query the implicit include paths from the compiler later in
   * CodeChecker. If we resolve the symlink, then the implicit include
   * path getter command line arguments go to CCache binary. The solution
   * is not to resolve the symlinks in the logger.
   */
  if (prog_ && prog_[0] != '/')
    path_ptr = findFullPath(prog_, full_prog_path);

  if (path_ptr) /* Log compiler with full path. */
    loggerVectorAdd(&action->arguments, loggerStrDup(full_prog_path));
  else  /* Compiler was not found in path, log the binary name only. */
    loggerVectorAdd(&action->arguments, loggerStrDup(prog_));

  /* Determine programming language based on compiler name. */
  for (i = 0; cCompiler[i]; ++i)
    if (strstr(toolName, cCompiler[i]))
      lang = C;

  for (i = 0; cppCompiler[i]; ++i)
    if (strstr(toolName, cppCompiler[i]))
      lang = CPP;

  for (i = 1; argv_[i]; ++i)
  {
    const char* current = argv_[i];

    if (current[0])
      loggerVectorAdd(&action->arguments, loggerStrDup(current));

    if (current[0] == '-')
    {
      /* Determine the position of the last -I and -isystem flags.
       * Depending on whether the parameter of -I or -isystem is separated
       * from the flag by a space character.
       * 2 == strlen("-I") && 8 == strlen("-isystem")
       */
      if (startsWith(current, "-I"))
        lastIncPos = action->arguments.size + (current[2] ? 0 : 1);
      else if (startsWith(current, "-isystem"))
        lastSysIncPos = action->arguments.size + (current[8] ? 0 : 1);

      /* Determine the programming language based on -x flag.
       */
      else if (startsWith(current, "-x"))
      {
        /* TODO: The language value after -x can be others too. See the man
         * page of GCC.
         * TODO: According to a GCC warning the -x flag has no effect when it
         * is placed after the last input file to be compiled.
         */
        const char* l = current[2] ? current + 2 : argv_[i + 1];
        if (strcmp(l, "c") == 0 || strcmp(l, "c-header") == 0)
          lang = C;
        else if (strcmp(l, "c++") == 0 || strcmp(l, "c++-header") == 0)
          lang = CPP;
      }

      /* Determining the output of the build command. In some cases some .o or
       * or other files may be considered a source file when they are a
       * parameter of a flag other than -o, such as -MT. The only usage of
       * collecting action->output is to remove it from action->sources later.
       */
      else if (startsWith(current, "-o"))
      {
        loggerFileInitFromPath(
          &action->output,
          current[2] ? current + 2 : argv_[i + 1]);
      }
    }
    else
    {
      char* ext = loggerGetFileExt(current, 1);
      if (ext)
      {
        int i;
        for (i = 0; srcExts[i]; ++i)
        {
          if (strcmp(srcExts[i], ext) == 0)
          {
            char newPath[PATH_MAX];

            if (getenv("CC_LOGGER_ABS_PATH"))
            {
              loggerMakePathAbs(current, newPath, 0);
            }
            else
            {
              strcpy(newPath, current);
            }
            loggerVectorAddUnique(&action->sources, loggerStrDup(newPath),
              (LoggerCmpFuc) &strcmp);
            break;
          }
        }
      }
      free(ext);
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

  if (getenv("CC_LOGGER_ABS_PATH"))
    transformSomePathsAbsolute(&action->arguments);

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
  {
    loggerVectorAdd(actions_, action);
  }
  else if ((responseFile = getResponseFile(&action->arguments)))
  {
    LOG_INFO("Processing response file: %s", responseFile);
    loggerVectorAdd(&action->sources, responseFile);
    loggerVectorAdd(actions_, action);
  }
  else
  {
    LOG_WARN("No souce file was found.");
  }

  return 1;
}
