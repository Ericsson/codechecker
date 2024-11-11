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
  /// This algorithm encapsulates two escaping operations in this order:
  /// 1) shell-escape
  /// 2) json-escape
  /// We need to do this, since we want to embed the shell-command into
  /// the compile_command.json.
  ///
  /// However, we will need an additional escaping, since we
  /// want to embed these strings into a json string value.
  /// Hence, we will need to escape each backslash again.
  /// We also need to escape the quote characters too.
  ///
  /// Examples: <input> -> <shell-escaped> -> <json-escaped>
  ///   ['\t'] -> ['\\',  't'] -> ['\\', '\\',  't']
  ///   ['\\'] -> ['\\', '\\'] -> ['\\', '\\',  '\\', '\\']
  ///   ['"']  -> ['\\',  '"'] -> ['\\', '\\',  '\\', '"']
  ///
  /// We apply these two escape operations together.

  int size = 0;
  while (*str_)
  {
    // 0x1B is '\e' (ESC)
    if (strchr("\a0x1B\t\b\f\r\v\n ", *str_))
      size += 3; // backslash, backslash, (a|e|t|b|f|r|v| |n)
    else if (*str_ == '"' || *str_ == '\\')
      size += 4; // backslash, backslash, backslash, ('"' or '\\')
    else if ((unsigned char)*str_ < 0x20)
      size += 5; // backslash, backslash, 'x', hex-digit, hex-digit
    else
      size += 1; // no-escaping required, simply copy
    ++str_;
  }

  /* For closing \0 character. */
  ++size;

  return size;
}

char* shellEscapeStr(const char* str_, char* buff_)
{
  // Check the 'predictEscapedSize' for details about this.
  char* out = buff_;

  while (*str_)
  {
    switch (*str_)
    {
      case '\a':
        *out++ = '\\';
        *out++ = '\\';
        *out++ = 'a';
        break;
      case 0x1B: // '\e' (ESC)
        *out++ = '\\';
        *out++ = '\\';
        *out++ = 'e';
        break;
      case '\t':
        *out++ = '\\';
        *out++ = '\\';
        *out++ = 't';
        break;
      case '\b':
        *out++ = '\\';
        *out++ = '\\';
        *out++ = 'b';
        break;
      case '\f':
        *out++ = '\\';
        *out++ = '\\';
        *out++ = 'f';
        break;
      case '\r':
        *out++ = '\\';
        *out++ = '\\';
        *out++ = 'r';
        break;
      case '\v':
        *out++ = '\\';
        *out++ = '\\';
        *out++ = 'v';
        break;
      case '\n':
        *out++ = '\\';
        *out++ = '\\';
        *out++ = 'n';
        break;
      case ' ':
        *out++ = '\\';
        *out++ = '\\';
        *out++ = ' ';
        break;
      case '\\':
        *out++ = '\\';
        *out++ = '\\';
        *out++ = '\\';
        *out++ = '\\';
        break;
      case '\"':
        *out++ = '\\';
        *out++ = '\\';
        *out++ = '\\';
        *out++ = '\"';
        break;
      default: {
        // Escape the rest of the control characters, which were not handled
        // separately:
        //   0-8: control codes (NUL, SOH, STX, ..., BEL, BS)
        //     9: '\t' (tab)
        // 10-13: whitespaces ['\n', '\v', '\f', '\r']
        // 14-31: control codes: (SO, SI, DLE, ..., RS, US)
        // 32-126: regular printable characters
        //
        // 32 == 0x20
        unsigned char value = *str_;
        if (value < 0x20) {
          static const unsigned char dec2hex_last_digit[0x20] = {
            '0','1','2','3','4','5','6','7','8','9', 'A', 'B', 'C', 'D', 'E', 'F',
            '0','1','2','3','4','5','6','7','8','9', 'A', 'B', 'C', 'D', 'E', 'F',
          };
          *out++ = '\\';
          *out++ = '\\';
          *out++ = 'x';
          *out++ = (value < 0x10 ? '0' : '1');
          *out++ = dec2hex_last_digit[value];
          break;
        }
        // Otherwise no escaping required.
        *out++ = *str_;
        break;
      }
    }
    ++str_; // Advance to the next unprocessed character.
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

void logPrint(char* logLevel_, char* fileName_, int line_, char *fmt_,...)
{
  const char* debugFile = getenv("CC_LOGGER_DEBUG_FILE");
  if (!debugFile)
  {
    return;
  }

  int lockFd;
  int logFd;
  FILE* stream;

  lockFd = aquireLock(debugFile);
  if (lockFd == -1)
  {
    return;
  }

  logFd = open(debugFile, O_CREAT | O_RDWR, S_IRUSR | S_IWUSR);
  if (logFd == -1)
  {
    freeLock(lockFd);
    return;
  }

  stream = fdopen(logFd, "a");
  if (!stream)
  {
    close(logFd);
    freeLock(lockFd);
    return;
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
}
