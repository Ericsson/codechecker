/**
 * -------------------------------------------------------------------------
 *                     The CodeChecker Infrastructure
 *   This file is distributed under the University of Illinois Open Source
 *   License. See LICENSE.TXT for details.
 * -------------------------------------------------------------------------
 */

#include "ldlogger-tool.h"
#include "ldlogger-util.h"
#include "ldlogger-hooks.h"

#include <sys/types.h>
#include <sys/stat.h>
#include <sys/file.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include <ctype.h>

static char* createJsonCommandString(const LoggerVector* args_)
{
  size_t cmdSize = 1;  /* For closing \0 character. */
  char* cmd;
  char* currEnd;
  size_t i;

  /* Calculate the length of the output buffer. */
  for (i = 0; i < args_->size; ++i)
  {
    /*
      In the output buffer the command line arguments will be separated by a
      space character. However, the predictEscapedSize() returns the size of
      the predicted length including the closing \0 characters which will be
      replaced by space.
    */
    cmdSize += predictEscapedSize((const char*) args_->data[i]);
  }

  cmd = (char*) malloc(sizeof(char) * cmdSize);
  if (!cmd)
  {
    return NULL;
  }

  currEnd = cmd;
  currEnd += strlen(shellEscapeStr((const char*) args_->data[0], currEnd));
  for (i = 1; i < args_->size; ++i)
  {
    *currEnd = ' ';
    ++currEnd;
    currEnd += strlen(shellEscapeStr((const char*) args_->data[i], currEnd));
  }

  *currEnd = '\0';
  return cmd;
}

static void writeAction(
  FILE* stream_,
  char const* wd_,
  const LoggerAction* action_,
  int* entryCount_)
{
  size_t i;
  char* command;

  command = createJsonCommandString(&action_->arguments);
  if (!command)
  {
    return;
  }

  for (i = 0; i < action_->sources.size; ++i)
  {
    if (++(*entryCount_) > 1)
    {
      fprintf(stream_, "\t,\n");
    }

    fprintf(stream_,
      "\t{\n" \
      "\t\t\"directory\": \"%s\",\n" \
      "\t\t\"command\": \"%s\",\n" \
      "\t\t\"file\": \"%s\"\n" \
      "\t}\n",
      wd_,                                    /* directory */
      command,                                /* command */
      (const char*) action_->sources.data[i]  /* file */
    );
  }

  free(command);
}

static void writeActions(FILE* stream_, char const* wd_, const LoggerVector* actions_)
{
  size_t i;
  long fsize;
  int entryCount = 0;

  if (actions_->size <= 0)
  {
    return;
  }

  fseek(stream_, 0L, SEEK_END);
  fsize = ftell(stream_);
  if (fsize == 0)
  {
    /* This is a new file, should write a [ char */
    fprintf(stream_, "[\n");
  }
  else
  {
    /* We should overwrite the ] character at the end to get a valid
       json file at the end
    */
    fseek(stream_, -1L, SEEK_END);
    if (fsize > 5)
    {
      /* This json is not empty, we should write ',' characters */
      ++entryCount;
    }
  }

  for (i = 0; i < actions_->size; ++i)
  {
    writeAction(stream_, wd_, (const LoggerAction*) actions_->data[i], &entryCount);
  }

  fprintf(stream_, "]");

  /* An fclose also closes the file descriptor, so wo only call an fflush
   * here */
  fflush(stream_);
}

static int aquireLock(char const* logFile_)
{
  char lockFilePath[PATH_MAX];
  int lockFile;

  if (!loggerMakePathAbs(logFile_, lockFilePath, 0))
  {
    return -1;
  }

  strcat(lockFilePath, ".lock");
  lockFile = open(lockFilePath, O_RDWR | O_CREAT, S_IRUSR | S_IWUSR);
  if (lockFile == -1)
  {
    return -1;
  }

  if (flock(lockFile, LOCK_EX) == -1)
  {
    close(lockFile);
    return -1;
  }

  return lockFile;
}

static void freeLock(int lockFile_)
{
  if (lockFile_ != -1)
  {
    flock(lockFile_, LOCK_UN);
    close(lockFile_);
  }
}

static void logProgramArgs(
  FILE* stream_,
  char const* prog_,
  int argc_,
  char const* argv_[])
{
  char const** argList;
  LoggerVector actions;
  char workingDir[PATH_MAX];

  if (!loggerMakePathAbs(".", workingDir, 1))
  {
    return;
  }

  /* Convert argument vector to a NULL terminated list */
  argList = (char const **) malloc(sizeof(char*) * (argc_ + 1));
  if (argList)
  {
    memcpy(argList, argv_, sizeof(char*) * argc_);
    argList[argc_] = NULL;
  }
  else
  {
    return;
  }

  loggerVectorInitAdv(&actions, 10, (LoggerFreeFuc) &loggerActionFree);

  loggerCollectActionsByProgName(prog_, argList, &actions);

  writeActions(stream_, workingDir, &actions);

  loggerVectorClear(&actions);
  free(argList);
}

/**
 * Logger entry point.
 *
 * The first argument should be the first argument of the exec* call, the rest
 * is the argument vector.
 *
 * @param argc_ argument counter.
 * @param argv_ argument vector (see above).
 * @return see a UNIX book.
 */
int logExec(int argc_, char const* argv_[])
{
  int lockFd;
  int logFd;
  FILE* stream;
  char const* logFileEnv;

  if (argc_ < 2)
  {
    return -1;
  }

  logFileEnv = getenv("CC_LOGGER_FILE");
  if (!logFileEnv)
  {
    return -3;
  }

  lockFd = aquireLock(logFileEnv);
  if (lockFd == -1)
  {
    return -5;
  }

  logFd = open(logFileEnv, O_CREAT | O_RDWR, S_IRUSR | S_IWUSR);
  if (logFd == -1)
  {
    freeLock(lockFd);
    return -7;
  }

  stream = fdopen(logFd, "w+");
  if (!stream)
  {
    close(logFd);
    freeLock(lockFd);
    return -9;
  }

  logProgramArgs(stream, argv_[0], argc_ - 1, argv_ + 1);

  fclose(stream); /* fclose also calls close() */
  freeLock(lockFd);

  return 0;
}

#ifdef __LOGGER_MAIN__
int main(int argc_, char const* argv_[])
{
  return logExec(argc_ - 1, argv_ + 1);
}
#endif
