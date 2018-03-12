/**
 * -------------------------------------------------------------------------
 *                     The CodeChecker Infrastructure
 *   This file is distributed under the University of Illinois Open Source
 *   License. See LICENSE.TXT for details.
 * -------------------------------------------------------------------------
 */

#ifndef __LOGGER_UTIL_H__
#define __LOGGER_UTIL_H__

#include <limits.h>
#include <linux/limits.h>
#include <string.h>

/**
 * Generates a shell-escaped version of the given string. The output buffer
 * must be large enough (recommended size is strlen(str_) * 2 + 1).
 * 
 * @param str_ a string to escape (non null).
 * @param buff_ an output buffer (non null).
 * @return anways returns buff_.
 */
char* shellEscapeStr(const char* str_, char* buff_);

/**
 * Resolves a given path to an absolute path. The given buffer (resolved) may
 * be modified on error.
 *
 * @param path_ a relative or absolute path.
 * @param resolved_ a buffer for resolved path (must be at least PATH_MAX).
 * @param mustExist_ if it true than makePathAbsolute chech if the file exists.
 * @return resolved_ or NULL on error.
 */
char* loggerMakePathAbs(const char* path_, char* resolved_, int mustExist_);

/**
 * Typedef for free function for a vector.
 */
typedef void (*LoggerFreeFuc)(void*);

/**
 * Typedef for dup function for a vector.
 */
typedef void* (*LoggerDupFuc)(const void*);

/**
 * Typedef for cmp function for a vector.
 */
typedef int (*LoggerCmpFuc)(const void*, const void*);

/**
 * Typedef for predicate function for a vector. This should return 0 if the
 * condition is not true for the element.
 */
typedef int (*LoggerPredFuc)(const void*);

/**
 * A very simple vector.
 */
typedef struct _LoggerVector 
{
  /**
   * The actual size of the vector.
   */
  size_t size;
  /**
   * The capacity of the vector.
   */
  size_t capacity;
  /**
   * Free function for data elements.
   */
  LoggerFreeFuc dataFree;
  /**
   * Data array.
   */
  void** data;
} LoggerVector;

/**
 * Inits an empty vector.
 *
 * @param vec_ a vector struct (must be not NULL).
 * @return the vec_ param or NULL on error.
 */
LoggerVector* loggerVectorInit(LoggerVector* vec_);

/**
 * An advanced version of loggerVectorInit.
 *
 * @param vec_ a vector struct (must be not NULL).
 * @param cap_ inital capacity.
 * @param freeFunc_ free function for data (it could be NULL).
 * @return the vec_ param or NULL on error.
 */
LoggerVector* loggerVectorInitAdv(
  LoggerVector* vec_,
  size_t cap_,
  LoggerFreeFuc freeFunc_);

/**
 * Clears the vector (after it you can free the vector without memory leaks or
 * you can call a loggerVectorInit* on it).
 *
 * @param vec_ a vector struct (must be not NULL).
 */
void loggerVectorClear(LoggerVector* vec_);

/**
 * Adds all element from the source vector to the vec_ param using the dup_
 * function for duplicating the elements.
 *
 * @param vec_ a vector.
 * @param source_ source vector.
 * @param position_ position where the new elements are inserted (optional)
 * @param dup_ a function to duplicate items.
 * @return zero on error, non-zero on success.
 */
int loggerVectorAddFrom(
  LoggerVector* vec_,
  const LoggerVector* source_,
  const size_t* position_,
  LoggerDupFuc dup_);

/**
 * Adds an item to a vector. The element will be owned by the vector and
 * freed by dataFree function (if it not null).
 *
 * @param vec_ a vector struct (must be not NULL).
 * @param data_ an item.
 * @return zero on error, non-zero on success.
 */
int loggerVectorAdd(LoggerVector* vec_, void* data_);

/**
 * Like loggerVectorAdd() but first it tries to find the element in the vector
 * using the given comparation fuction and if there is a match, the functions
 * simply returns with success (after it freed the data_).
 *
 * @param vec_ a vector struct (must be not NULL).
 * @param data_ an item.
 * @param cmp_ a comparation function.
 * @return zero on error, non-zero on success.
 */
int loggerVectorAddUnique(LoggerVector* vec_, void* data_, LoggerCmpFuc cmp_);

/**
 * Removes (and frees) an item from the vector.
 *
 * @param vec_ a vector struct (must be not NULL).
 * @parma index_ an item index.
 */
void loggerVectorErase(LoggerVector* vec_, size_t index_);

/**
 * Finds an element using the given comparation fuction.
 *
 * @param vec_ a vector struct (must be not NULL).
 * @param data_ an item.
 * @param cmp_ a comparation function.
 * @return SIZE_MAX if the element not found otherwise the item`s index.
 */
size_t loggerVectorFind(
  LoggerVector* vec_,
  const void* data_,
  LoggerCmpFuc cmp_);

/**
 * Finds an element using the given predicate fuction.
 *
 * @param vec_ a vector struct (must be not NULL).
 * @param pred_ a predicate function.
 * @return SIZE_MAX if the element not found otherwise the item`s index.
 */
size_t loggerVectorFindIf(
  LoggerVector* vec_,
  LoggerPredFuc pred_);

/**
 * An strdup implementation (its not in ANSI C).
 *
 * @param str_ string to duplicate.
 * @return a newly allocated duplicate of str_.
 */
char* loggerStrDup(const char* str_);

/**
 * An strndup implementation (its not in ANSI C).
 *
 * @param str_ string to duplicate.
 * @param n_ max number of chars to duplicate.
 * @return a newly allocated duplicate of str_.
 */
char* loggerStrNDup(const char* str_, size_t n_);

/**
 * Return the file`s extension.
 *
 * @param path_ the path of the file.
 * @param tolower_ if it true, the extension will be converted to lower-cased.
 * @return the file extension or NULL if no extension.
 */
char* loggerGetFileExt(const char* path_, int tolower_);

/**
 * Returns the file`s directory.
 *
 * @param absPath_ the absolute file path.
 * @return parent directory or NULL on error.
 */
char* loggerGetFileDir(const char* absPath_);

/**
 * Returns the absolute file name without extension.
 *
 * @param absPath_ the absolute file path.
 * @return the absolute file name without extension or NULL on error.
 */
char* loggerGetFilePathWithoutExt(const char* absPath_);

/**
 * Return the file`s name with or without it`s extension.
 * 
 * @param absPath_ the absolute file path.
 * @param withoutExt_ with or without extension.
 * @return file name or NULL on error..
 */
char* loggerGetFileName(const char* absPath_, int withoutExt_);

#endif /* __LOGGER_UTIL_H__ */

