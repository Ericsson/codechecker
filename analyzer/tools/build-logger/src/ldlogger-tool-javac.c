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
#include <stdio.h>
#include <stdlib.h>
#include <assert.h>
#include <wordexp.h>
#include <string.h>
#include <ctype.h>

/**
 * States for javac argument parser.
 */
typedef enum _JavaArgsState
{
  /**
   * Normal state (default).
   */
  Normal,
  /**
   * After a -d paramater.
   */
  InClassDir,
  /**
   * After a -cp or -classpath paramater.
   */
  InClassPath
} JavaArgsState;

/**
 * Reads the arguments from a file (for ant support).
 *
 * @param file_ a file that contains the sources.
 * @param args_ a vector for arguments.
 */
static void readArgumentsFromFile(const char* file_, LoggerVector* args_)
{
  char* line = NULL;
  size_t lineSize = 0;
  ssize_t readSize;
  
  FILE* file = fopen(file_, "r");
  if (!file)
  {
    return;
  }

  while ((readSize = getline(&line, &lineSize, file)) > 0)
  {
    char* cont;
    char* normLine;

    /* The file may contain '"' character at the begining and the end of the
     * line, so we have to cut them off. */
    for (cont = line; cont[0] && (isspace(cont[0]) || cont[0] == '"');++cont){}
    normLine = loggerStrDup(cont);
    for (cont = normLine; cont[0] && cont[0] != '"'; ++cont) {}
    *cont = 0;

    loggerVectorAdd(args_, normLine);
  }

  fclose(file);
}

/**
 * Data struct for the javac parser function.
 */
typedef struct _ParserData
{
  /**
   * "true" if we have a source path in the argument vector.
   */
  int hasSourcePath;
  /**
   * The current state (see the enum at the head of this file).
   */
  JavaArgsState state;
  /**
   * Vector for the common arguments (without source or class files).
   */
  LoggerVector commonArgs;
  /**
   * Vector for the source files.
   */
  LoggerVector sources;
  /**
   * Class directory (-d parameter) or empty string.
   */
  char classdir[PATH_MAX];
} ParserData;

/**
 * Handles a class path argument (resolves the globs and makes relative paths).
 * The result will be in the *resCp_ buffer. If there is not enough space in
 * the memory buffer then the buffer will be reallocated and its new size
 * stored in the *resCpSize_ parameter.
 *
 * @param resCp_ a pointer to a memory buffer.
 * @param resCpSize_ a pointer to the current size of the *resCp_ buffer.
 * @param cp_ the unresolved class path (-cp or -classpath parameter).
 * @return 0 on error, non 0 on success.
 */
static int handleClassPath(
  char** resCp_,
  size_t* resCpSize_,
  char const* cp_)
{
  char* classPath;
  size_t currSize = 1;
  char* cpPart;

  **resCp_ = 0;
  classPath = (char*) malloc((strlen(cp_) + 1) * sizeof(char));
  strcpy(classPath, cp_);

  for (cpPart = strtok(classPath, ":"); cpPart; cpPart = strtok(NULL, ":"))
  {
    size_t i;
    char** words;
    wordexp_t we;
   
    memset(&we, 0, sizeof(wordexp_t));
    if (wordexp(cpPart, &we, WRDE_NOCMD | WRDE_UNDEF) != 0)
    {
      strcpy(*resCp_, cp_);
      free(classPath);
      return 0;
    }

    words = we.we_wordv;
    for (i = 0; i < we.we_wordc; i++)
    {
      char path[PATH_MAX];
      if (loggerMakePathAbs(words[i], path, 1) == NULL)
      {
        /* The path is malformed or does not exists! Ignore */
        continue;
      }

      /* We need space for the path + a ':' character */
      currSize += strlen(path) + 1;
      if (currSize >= *resCpSize_)
      {
        char* newMem = realloc(*resCp_, currSize * 2);
        if (!newMem)
        {
          /* Out of memory */
          strcpy(*resCp_, cp_);
          free(classPath);
          wordfree(&we);
          return 0;
        }

        *resCp_ = newMem;
        *resCpSize_ = currSize * 2;
      }

      strcat(*resCp_, path);
      strcat(*resCp_, ":");
    }

    wordfree(&we);
  }

  /* Cut down the last ':' character */
  currSize = strlen(*resCp_);
  if ((*resCp_)[currSize - 1] == ':')
  {
    (*resCp_)[currSize - 1] = 0;
  }

  free(classPath);
  return 1;
}

/**
 * Processes a single argument.
 *
 * @param arg_ the current argument.
 * @param data_ the state data of the parser function.
 */
static void processArg(const char* arg_, ParserData* data_)
{
  size_t argToAddSize = PATH_MAX;
  char* argToAdd ;
  char* ext;

  argToAdd = (char*) malloc(sizeof(char) * argToAddSize);
  if (!argToAdd)
  {
    /* NO MEM! */
    return;
  }

  strcpy(argToAdd, arg_);

  if (data_->state == InClassDir)
  {
    if (!loggerMakePathAbs(arg_, data_->classdir, 0))
    {
      strcpy(data_->classdir, arg_);
    }

    strcpy(argToAdd, data_->classdir);
    data_->state = Normal;
  }
  else if (data_->state == InClassPath)
  {
    handleClassPath(&argToAdd, &argToAddSize, arg_);
    data_->state = Normal;
  }
  else if (strcmp(arg_, "-sourcepath") == 0)
  {
    data_->hasSourcePath = 1;
  }
  else if (strcmp(arg_, "-d") == 0)
  {
    data_->state = InClassDir;
  }
  else if (strcmp(arg_, "-cp") == 0 || strcmp(arg_, "-classpath") == 0)
  {
    data_->state = InClassPath;
  }
  else if ((ext = loggerGetFileExt(arg_, 1)))
  {
    int isSource = 0;
    if (strcmp(ext, "java") == 0)
    {
      char path[PATH_MAX];
      if (loggerMakePathAbs(arg_, path, 0))
      {
        loggerVectorAddUnique(&data_->sources,
          loggerStrDup(path), (LoggerCmpFuc) &strcmp);
        isSource = 1;
      }
    }

    if (isSource)
    {
      argToAdd[0] = 0;
    }

    free(ext);
  }

  if (argToAdd[0])
  {
    loggerVectorAdd(&data_->commonArgs, loggerStrDup(argToAdd));
  }

  free(argToAdd);
}

int loggerJavacParserCollectActions(
  const char* prog_,
  const char* const argv_[],
  LoggerVector* actions_)
{
  ParserData data;
  size_t i;

  assert(prog_ == prog_); /* suppress unused variable */

  data.hasSourcePath = 0;
  data.state = Normal;
  loggerVectorInit(&data.commonArgs);
  loggerVectorInit(&data.sources);
  memset(data.classdir, 0, sizeof(data.classdir));

  loggerVectorAdd(&data.commonArgs, loggerStrDup(prog_));

  for (i = 1; argv_[i]; ++i)
  {
    if (argv_[i][0] == '@')
    {
      size_t j;
      LoggerVector fargs;

      loggerVectorInit(&fargs);
      
      readArgumentsFromFile(argv_[i] + 1, &fargs);
      for (j = 0; j < fargs.size; ++j)
      {
        processArg((const char*) fargs.data[j], &data);
      }

      loggerVectorClear(&fargs);
    }
    else
    {
      processArg(argv_[i], &data);
    }
  }

  if (!data.hasSourcePath)
  {
    char workdir[PATH_MAX];
    if (loggerMakePathAbs(".", workdir, 0))
    {
      loggerVectorAdd(&data.commonArgs, loggerStrDup("-sourcepath"));
      loggerVectorAdd(&data.commonArgs, loggerStrDup(workdir));
    }
  }

  for (i = 0; i < data.sources.size; ++i)
  {
    char outputFile[PATH_MAX];
    const char* src = (char*) data.sources.data[i];
    LoggerAction* action = loggerActionNew();
    if (!action)
    {
      continue;
    }

    loggerVectorAddFrom(&action->arguments, &data.commonArgs,
      NULL, (LoggerDupFuc) &loggerStrDup);
    loggerVectorAdd(&action->arguments, loggerStrDup(src));
    loggerVectorAdd(&action->sources, loggerStrDup(src));

    if (data.classdir[0] != 0)
    {
      char* fname = loggerGetFileName(src, 1);
      strcpy(outputFile, data.classdir);
      strcat(outputFile, "/");
      strcat(outputFile, fname);
      strcat(outputFile, ".class");
      free(fname);
    }
    else
    {
      char* path = loggerGetFilePathWithoutExt(src);
      strcpy(outputFile, path);
      strcat(outputFile, ".class");
      free(path);
    }

    loggerFileInitFromPath(&action->output, outputFile);
    loggerVectorAdd(actions_, action);
  }

  loggerVectorClear(&data.commonArgs);
  loggerVectorClear(&data.sources);

  return 1;
}

