/**
 * -------------------------------------------------------------------------
 *  Part of the CodeChecker project, under the Apache License v2.0 with
 *  LLVM Exceptions. See LICENSE for license information.
 *  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
 * -------------------------------------------------------------------------
 */

#include "ldlogger-util.h"

#include <assert.h>
#include <ctype.h>
#include <fcntl.h>
#include <limits.h>
#include <stdarg.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>

static char* makePathAbsRec(const char* path_, char* resolved_)
{
  char pathBuff[PATH_MAX];
  char* slashPos;
  char* child;

  if (realpath(path_, pathBuff))
  {
    pathBuff[PATH_MAX - 1] = 0;
    return strcpy(resolved_, pathBuff);
  }
  else
  {
    strcpy(pathBuff, path_);
  }

  /* cut off the last part */
  slashPos = strrchr(pathBuff, '/');
  if (!slashPos || slashPos == path_)
  {
    return NULL;
  }

  child = slashPos + 1;
  if (strcmp(child, ".") == 0 || strcmp(child, "..") == 0)
  {
    /* Won't work: the result will be relative. */
    return NULL;
  }

  *slashPos = 0;
  if (makePathAbsRec(pathBuff, resolved_))
  {
    strcat(resolved_, "/");
    strcat(resolved_, child);
    return resolved_;
  }

  return NULL;
}

/**
 * Returns formatted current time.
 *
 * @param buff_ an output buffer (non null).
 * @return anways returns buff_.
 */
static void getCurrentTime(char* buff_)
{
  time_t rawtime;
  struct tm* timeinfo;

  time(&rawtime);
  timeinfo = localtime(&rawtime);

  strftime(buff_, 26, "%Y-%m-%d %H:%M:%S", timeinfo);
}

int predictEscapedSize(const char* str_)
{
  int size = 0;

  while (*str_)
  {
    if (strchr("\t\b\f\r\v\n ", *str_))
      size += 2;
    else if (*str_ == '"' || *str_ == '\\')
      /* The quote (") and backslash (\) needs an extra escaped escape
         character because the JSON string literals are surrounded by quote
         by default. */
      size += 3;

    ++size;
    ++str_;
  }

  /* For closing \0 character. */
  ++size;

  return size;
}

char* shellEscapeStr(const char* str_, char* buff_)
{
  char* out = buff_;

  while (*str_)
  {
    switch (*str_)
    {
      case '\t':
      case '\b':
      case '\f':
      case '\r':
      case '\v':
      case '\n':
      case ' ':
        *out++ = '\\';
        *out++ = '\\';
        *out++ = *str_++;
        break;

      case '\\':
      case '\"':
        *out++ = '\\';
        *out++ = '\\';
        *out++ = '\\';
        *out++ = *str_++;
        break;

      default:
        *out++ = *str_++;
        break;
    }
  }

  *out = '\0';
  return buff_;
}

int startsWith(const char* str_, const char* prefix_)
{
  return strstr(str_, prefix_) == str_;
}

char* loggerMakePathAbs(const char* path_, char* resolved_, int mustExist_)
{
  assert(resolved_ && "resolved_ must be not NULL!");

  if (!path_ || path_[0] == '\0')
  {
    return NULL;
  }

  if (mustExist_ && access(path_, F_OK) != 0)
  {
    return NULL;
  }

  if (path_[0] != '/')
  {
    /* This is a relative path, prepend the current working dir */
    char newPath[PATH_MAX];
    if (!getcwd(newPath, PATH_MAX))
    {
      return NULL;
    }

    strcat(newPath, "/");
    strcat(newPath, path_);
    return makePathAbsRec(newPath, resolved_);
  }

  return makePathAbsRec(path_, resolved_);
}

LoggerVector* loggerVectorInit(LoggerVector* vec_)
{
  return loggerVectorInitAdv(vec_, 10, &free);
}

LoggerVector* loggerVectorInitAdv(
  LoggerVector* vec_,
  size_t cap_,
  LoggerFreeFuc freeFunc_)
{
  assert(vec_ && "vec_ must be not NULL");

  vec_->size = 0;
  vec_->capacity = cap_;
  vec_->dataFree = freeFunc_;

  if (cap_ > 0)
  {
    vec_->data = (void**) malloc(sizeof(void*) * cap_);
    if (!vec_->data)
    {
      return NULL;
    }
  }
  else
  {
    vec_->data = NULL;
  }

  return vec_;
}

void loggerVectorClear(LoggerVector* vec_)
{
  assert(vec_ && "vec_ must be not NULL");

  if (vec_->data)
  {
    if (vec_->dataFree)
    {
      size_t i;
      for (i = 0; i < vec_->size; ++i)
      {
        vec_->dataFree(vec_->data[i]);
      }
    }

    free(vec_->data);

    vec_->data = NULL;
    vec_->capacity = 0;
    vec_->size = 0;
  }
}

int loggerVectorAddFrom(
  LoggerVector* vec_,
  const LoggerVector* source_,
  const size_t* position_,
  LoggerDupFuc dup_)
{
  size_t i;
  size_t reqCap;
  size_t insPos;

  assert(vec_ && "vec_ must be not NULL");
  assert(source_ && "source_ must be not NULL");
  assert(dup_ && "dup_ must be not NULL");
  assert((!position_ || *position_ <= vec_->size) && "position_ is out of range!");

  reqCap = vec_->size + source_->size;

  if (position_)
  {
    insPos = *position_;
  }
  else
  {
    insPos = vec_->size;
  }

  if (vec_->capacity < reqCap)
  {
    void** newData = (void**) realloc(vec_->data, sizeof(void*) * reqCap);
    if (!newData)
    {
      return 0;
    }

    vec_->data = newData;
    vec_->capacity = reqCap;
  }

  if (insPos < vec_->size)
  {
    /* Move items to the end of the vector */
    for (i = vec_->size - 1; i >= insPos; --i)
    {
      vec_->data[i + source_->size] = vec_->data[i];
      vec_->data[i] = NULL;
    }
  }

  for (i = 0; i < source_->size; ++i)
  {
    vec_->data[i + insPos] = dup_(source_->data[i]);
  }

  vec_->size += source_->size;
  return 1;
}

int loggerVectorAdd(LoggerVector* vec_, void* data_)
{
  assert(vec_ && "vec_ must be not NULL");

  if (!data_)
  {
    return 0;
  }

  if (vec_->size == vec_->capacity)
  {
    size_t newCap = vec_->capacity ? vec_->capacity * 2 : 10;
    void** newData = (void**) realloc(vec_->data, sizeof(void*) * newCap);
    if (!newData)
    {
      return 0;
    }

    vec_->data = newData;
    vec_->capacity = newCap;
  }

  vec_->data[vec_->size] = data_;
  vec_->size += 1;

  return 1;
}

int loggerVectorAddUnique(LoggerVector* vec_, void* data_, LoggerCmpFuc cmp_)
{
  if (loggerVectorFind(vec_, data_, cmp_) != SIZE_MAX)
  {
    if (vec_->dataFree)
    {
      vec_->dataFree(data_);
    }

    return 2;
  }

  return loggerVectorAdd(vec_, data_);
}

size_t loggerVectorFind(
  LoggerVector* vec_,
  const void* data_,
  LoggerCmpFuc cmp_)
{
  size_t i;
  for (i = 0; i < vec_->size; ++i)
  {
    if (cmp_(data_, vec_->data[i]) == 0)
    {
      return i;
    }
  }

  return SIZE_MAX;
}

size_t loggerVectorFindIf(
  LoggerVector* vec_,
  LoggerPredFuc pred_)
{
  size_t i;
  for (i = 0; i < vec_->size; ++i)
    if (pred_(vec_->data[i]) != 0)
      return i;

  return SIZE_MAX;
}

void loggerVectorErase(LoggerVector* vec_, size_t index_)
{
  size_t i;

  if (index_ >= vec_->size)
  {
    return;
  }

  if (vec_->dataFree)
  {
    vec_->dataFree(vec_->data[index_]);
  }

  for (i = index_ + 1; i < vec_->size; ++i)
  {
    vec_->data[i-1] = vec_->data[i];
  }

  vec_->size -= 1;
}

void loggerVectorReplace(LoggerVector* vec_, size_t index_, void* data_)
{
  if (vec_->dataFree)
    vec_->dataFree(vec_->data[index_]);

  vec_->data[index_] = data_;
}

char* loggerStrDup(const char* str_)
{
  return loggerStrNDup(str_, strlen(str_));
}

char* loggerStrNDup(const char* str_, size_t n_)
{
  char* dup;
  size_t len = strlen(str_);
  if (len > n_)
  {
    len = n_;
  }

  dup = malloc(sizeof(char) * (len + 1));
  if (!dup)
  {
    return NULL;
  }

  memcpy(dup, str_, sizeof(char) * len);

  dup[len] = 0;
  return dup;
}

char* loggerGetFileExt(const char* path_, int tolower_)
{
  size_t i;
  size_t size;
  const char* ext;
  char* fname = loggerGetFileName(path_, 0);
  if (!fname)
  {
    return NULL;
  }

  ext = strrchr(fname, '.');
  if (!ext)
  {
    free(fname);
    return NULL;
  }

  ++ext;
  size = strlen(ext) + 1;
  for (i = 0; i < size; ++i)
  {
    if (tolower_)
    {
      fname[i] = tolower(ext[i]);
    }
    else
    {
      fname[i] = ext[i];
    }
  }

  return fname;
}

char* loggerGetFileDir(const char* absPath_)
{
  const char* slashPos = strrchr(absPath_, '/');
  if (slashPos == absPath_)
  {
    return loggerStrDup("/");
  }
  else if (slashPos)
  {
    return loggerStrNDup(absPath_,  slashPos - absPath_);
  }

  return NULL;
}

char* loggerGetFilePathWithoutExt(const char* absPath_)
{
  const char* extpos = strrchr(absPath_, '.');
  if (extpos)
  {
    return loggerStrNDup(absPath_, extpos - absPath_);
  }

  return loggerStrDup(absPath_);
}

char* loggerGetFileName(const char* absPath_, int withoutExt_)
{
  const char* fileName = strrchr(absPath_, '/');

  if (!fileName)
    fileName = absPath_;

  if (fileName[1] == 0)
    return NULL;

  ++fileName;
  if (withoutExt_)
  {
    const char* extpos = strrchr(fileName, '.');
    if (extpos)
    {
      return loggerStrNDup(fileName, extpos - fileName);
    }
  }

  return loggerStrDup(fileName);
}

int aquireLock(char const* logFile_)
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

void freeLock(int lockFile_)
{
  if (lockFile_ != -1)
  {
    flock(lockFile_, LOCK_UN);
    close(lockFile_);
  }
}

int logPrint(char* logLevel_, char* fileName_, int line_, char *fmt_,...)
{
  const char* debugFile = getenv("CC_LOGGER_DEBUG_FILE");
  if (!debugFile)
  {
    return 0;
  }

  int lockFd;
  int logFd;
  FILE* stream;

  lockFd = aquireLock(debugFile);
  if (lockFd == -1)
  {
    return -5;
  }

  logFd = open(debugFile, O_CREAT | O_RDWR, S_IRUSR | S_IWUSR);
  if (logFd == -1)
  {
    freeLock(lockFd);
    return -7;
  }

  stream = fdopen(logFd, "a");
  if (!stream)
  {
    close(logFd);
    freeLock(lockFd);
    return -9;
  }

  char currentTime[26];
  getCurrentTime(currentTime);

  fprintf(stream, "[%s %s][%s:%d] - ", logLevel_, currentTime, fileName_,
    line_);

  char* p, *str, **items;
  size_t num;
  size_t i;

  va_list args;
  va_start(args, fmt_);
  for (p = fmt_; *p; ++p)
  {
    if ( *p != '%' )
    {
      fputc(*p, stream);
    }
    else
    {
      switch ( *++p )
      {
        case 'a':
        {
          num = va_arg(args, size_t);
          items = va_arg(args, char**);
          for (i = 0; i < num; ++i)
          {
            fprintf(stream, "%s ", items[i]);
          }
          continue;
        }
        case 's':
        {
          str = va_arg(args, char *);
          fprintf(stream, "%s", str);
          continue;
        }
        case 'd':
        {
          num = va_arg(args, size_t);
          fprintf(stream, "%zu", num);
          continue;
        }
        default:
        {
          fputc(*p, stream);
        }
      }
    }
  }
  va_end(args);

  fputc('\n', stream);

  fclose(stream);
  freeLock(lockFd);

  return 0;
}
