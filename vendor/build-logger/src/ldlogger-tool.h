/**
 * -------------------------------------------------------------------------
 *                     The CodeChecker Infrastructure
 *   This file is distributed under the University of Illinois Open Source
 *   License. See LICENSE.TXT for details.
 * -------------------------------------------------------------------------
 */

#ifndef __LOGGER_TOOL_H__
#define __LOGGER_TOOL_H__

#include "ldlogger-util.h"

/**
 * Represent a file with an md5 sum.
 */
typedef struct _LoggerFile
{
  /**
   * File path.
   */
  char path[PATH_MAX];
} LoggerFile;

/**
 * Inits an instance form a path and calculates md5 sum for it.
 *
 * @param path_ file path.
 * @param file_ a file instance.
 * @return file_ or NULL on error.
 */
LoggerFile* loggerFileInitFromPath(LoggerFile* file_, const char* path_);

typedef struct _LoggerAction
{
  /**
   * The output of the action.
   */
  LoggerFile output;
  /**
   * The arguments of the execution (excluding the first (index 0) argument).
   */
  LoggerVector arguments;
  /**
   * Source files.
   */
  LoggerVector sources;
  /**
   * Tool`s name.
   */
  char toolName[PATH_MAX];
} LoggerAction;

/**
 * Creates a new action structure.
 *
 * @param toolName_ the name of the tool.
 * @return a new action instance or NULL on error.
 */
LoggerAction* loggerActionNew(const char* toolName_);

/**
 * Frees an action instance.
 * 
 * @param act_ an action.
 */
void loggerActionFree(LoggerAction* act_);

/**
 * Detects the tool by the program name and collects the build actions using
 * the appropriate parer functions (GCC, JAVAC, ...etc).
 *
 * @param prog_ the command path or the program name.
 * @param argv_ the arguments of the program (including the first one)
 * @param actions_ output vector for the build actions.
 * @return zero on error, non zero on success.
 */
int loggerCollectActionsByProgName(
  const char* prog_,
  const char* const argv_[],
  LoggerVector* actions_);

/**
 * Parser function for GCC like commands.
 *
 * @param prog_ the command path or the program name.
 * @param toolName_ the tools name.
 * @param argv_ the arguments of the program (including the first one)
 * @param actions_ output vector for the build actions.
 * @return zero on error, non zero on success.
 */
int loggerGccParserCollectActions(
  const char* prog_,
  const char* toolName_,
  const char* const argv_[],
  LoggerVector* actions_);

/**
 * Parser function for JavaC like commands.
 *
 * @param prog_ the command path or the program name.
 * @param toolName_ the tools name.
 * @param argv_ the arguments of the program (including the first one)
 * @param actions_ output vector for the build actions.
 * @return zero on error, non zero on success.
 */
int loggerJavacParserCollectActions(
  const char* prog_,
  const char* toolName_,
  const char* const argv_[],
  LoggerVector* actions_);

#endif /* __LOGGER_TOOL_H__ */

