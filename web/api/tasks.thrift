// -------------------------------------------------------------------------
//  Part of the CodeChecker project, under the Apache License v2.0 with
//  LLVM Exceptions. See LICENSE for license information.
//  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// -------------------------------------------------------------------------

include "codechecker_api_shared.thrift"

namespace py codeCheckerServersideTasks_v6
namespace js codeCheckerServersideTasks_v6

enum TaskStatus {
  ALLOCATED, // Non-terminated state. Token registered but the job hasn't queued yet: the input is still processing.
  ENQUEUED,  // Non-terminated state. Job in the queue, and all inputs are meaningfully available.
  RUNNING,   // Non-terminated state.
  COMPLETED, // Terminated state. Successfully ran to completion.
  FAILED,    // Terminated state. Job was running, but the execution failed.
  CANCELLED, // Terminated state. Job was cancelled by an administrator, and the cancellation succeeded.
  DROPPED,   // Terminated state. Job was cancelled due to system reasons (server shutdown, crash, other interference).
}

struct TaskInfo {
   1: codechecker_api_shared.TaskToken token,
   2: string                           taskKind,
   3: TaskStatus                       status,
  // If the task is associated with a product, this ID can be used to query
  // product information, see products.thirft service.
  // The 'productID' is set to 0 if there is no product associated, meaning
  // that the task is "global to the server".
   4: i64                              productId,
   5: string                           actorUsername,
   6: string                           summary,
  // Additional, human-readable comments, history, and log output from the
  // tasks's processing.
   7: string                           comments,
   8: i64                              enqueuedAtEpoch,
   9: i64                              startedAtEpoch,
  10: i64                              completedAtEpoch,
  11: i64                              lastHeartbeatEpoch,
  // Whether the administrator set this job for a co-operative cancellation.
  12: bool                             cancelFlagSet,
}

/**
 * TaskInfo with additional fields that is sent to administrators only.
 */
struct AdministratorTaskInfo {
  1: TaskInfo normalInfo,
  2: string   machineId,      // The hopefully unique identifier of the server
                              // that is/was processing the task.
  3: bool     statusConsumed, // Whether the main actor of the task
                              // (see normalInfo.actorUsername) consumed the
                              // termination status of the job.
}

/**
 * Metastructure that holds the filters for getTasks().
 * The individual fields of the struct are in "AND" relation with each other.
 * For list<> fields, elements of the list filter the same "column" of the
 * task information table, and are considered in an "OR" relation.
 */
struct TaskFilter {
   1: list<string>                   tokens,
   2: list<string>                   machineIDs,
   3: list<string>                   kinds,
   4: list<TaskStatus>               statuses,
  // If empty, it means "all", including those of no username.
   5: list<string>                   usernames,
  // If True, it means filter for **only** "no username".
  // Can not be set together with a non-empty "usernames".
   6: bool                           filterForNoUsername,
  // If empty, it means "all", including those of no product ID.
   7: list<i64>                      productIDs,
  // If True, it means filter for **only** "no product ID".
  // Can not be set together with a non-empty "productIDs".
   8: bool                           filterForNoProductID,
   9: i64                            enqueuedBeforeEpoch,
  10: i64                            enqueuedAfterEpoch,
  11: i64                            startedBeforeEpoch,
  12: i64                            startedAfterEpoch,
  13: i64                            completedBeforeEpoch,
  14: i64                            completedAfterEpoch,
  15: i64                            heartbeatBeforeEpoch,
  16: i64                            heartbeatAfterEpoch,
  17: codechecker_api_shared.Ternary cancelFlag,
  18: codechecker_api_shared.Ternary consumedFlag,
}

service codeCheckerServersideTaskService {
  // Retrieves the status of a task registered on the server, based on its
  // identifying "token".
  //
  // Following this query, if the task is in any terminating states and the
  // query was requested by the main actor, the status will be considered
  // "consumed", and might be garbage collected by the server at a later
  // point in time.
  //
  // If the server has authentication enabled, this query is only allowed to
  // the following users:
  //   * The user who originally submitted the request that resulted in the
  //     creation of this job.
  //   * If the job is associated with a specific product, anyone with
  //     PRODUCT_ADMIN privileges for that product.
  //   * Users with SUPERUSER rights.
  //
  // PERMISSION: <Situational>.
  TaskInfo getTaskInfo(
    1: codechecker_api_shared.TaskToken token)
    throws (1: codechecker_api_shared.RequestFailed requestError),

  // Returns privileged information about the tasks stored in the servers'
  // databases, based on the given filter.
  //
  // This query does not set the "consumed" flag on the results, even if the
  // querying user was a task's main actor.
  //
  // If the querying user only has PRODUCT_ADMIN rights, they are only allowed
  // to query the tasks corresponding to a product they are PRODUCT_ADMIN of.
  //
  // PERMISSION: SUPERUSER, PRODUCT_ADMIN
  list<AdministratorTaskInfo> getTasks(
    1: TaskFilter filters)
    throws (1: codechecker_api_shared.RequestFailed requestError),

  // Sets the specified task's "cancel" flag to TRUE, resulting in a request to
  // the task's execution to co-operatively terminate itself.
  // Returns whether the current RPC call was the one which set the flag.
  //
  // Tasks will generally terminate themselves at a safe point during their
  // processing, but there are no guarantees that a specific task at any given
  // point can reach such a safe point.
  // There are no guarantees that a specific task is implemented in a way that
  // it can ever be terminated via a "cancel" action.
  //
  // This method does not result in a communication via operating system
  // primitives to the running server, and it is not capable of either
  // completely shutting down a running server, or, conversely, to resurrect a
  // hung server.
  //
  // Setting the "cancel" flag of an already cancelled task does nothing, and
  // it is not possible to un-cancel a task.
  // Setting the "cancel" flag of already terminated tasks does nothing.
  // In both such cases, the RPC call will return "bool False".
  //
  // PERMISSION: SUPERUSER
  bool cancelTask(
    1: codechecker_api_shared.TaskToken token)
    throws (1: codechecker_api_shared.RequestFailed requestError),

  // Used for testing purposes only.
  // This function will **ALWAYS** throw an exception when ran outside of a
  // testing environment.
  //
  // The dummy task will increment a temporary counter in the background, with
  // intermittent sleeping, up to approximately "timeout" number of seconds,
  // after which point it will gracefully terminate.
  // The result of the execution is unsuccessful if "shouldFail" is a true.
  codechecker_api_shared.TaskToken createDummyTask(
    1: i32  timeout,
    2: bool shouldFail)
  throws (1: codechecker_api_shared.RequestFailed requestError),
}
