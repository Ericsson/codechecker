Server-side background task execution system
============================================

Introduction
------------

In order to facilitate the quick release of _API handler_ processes (so the server can reply to new _Thrift API_ requests), CodeChecker's **`server`** package implements support for the creation of **background tasks**.
A generic execution library deals with the **driver** aspects of background tasks, including the database handling (for cross-service synchronisation of task statuses) and memory management.

Each task is associated with a **`token`**, which is a random generated identifier, corresponding to the `PRIMARY KEY` in the database.
This token is used to query information about a task, and to execute administrative actions against the task.
Ancillary data, stored in the server's storage space on disk, is also keyed by the _`token`_.

The most important property of a _Task_ is its **status**, which can be:

* _`ALLOCATED`_: The task has its identifying token, and is under preparation.
* _`ENQUEUED`_: The task had been prepared and waiting for an executor to start the owork.
* _`RUNNING`_: The task is currently being executed.
* _`COMPLETED`_: The task's execution finished successfully.
* _`FAILED`_: The task's execution "structurally" failed due to an "inside" property of the execution. An uncaught `Exception` would have escaped the executor's _"main"_ method.
* _`CANCELLED`_: An administrator (**`SUPERUSER`**, see [the Permission system](permissions.md)) cancelled the execution of the task, and the task gracefully terminated itself.
* _`DROPPED`_: External influence resulted in the executing server's shutdown, and the task did not complete in a graceful way.

Task lifecycle
--------------

The workflow of a task's lifecycle is as follows:

### "Foreground" logic

Tasks are generally spawned by API handlers, executed in the control flow of a Thrift RPC function.

1. An **API** request arrives (later, this might be extended with a _`cron`_ -like scheduler) which exercises an endpoint that results in the need for a task.
2. _(Optionally)_ some conformance checks are executed on the input, in order to not even create the task if the input is ill-formed.
3. A task **`token`** is _`ALLOCATED`_: the record is written into the database, and now we have a unique identifier for the task.
4. The task is **pushed** to the _task queue_ of the CodeChecker server, resulting in the _`ENQUEUED`_ status.
5. The task's identifier **`token`** is returned to the user.
6. The API hander exits and the Thrift RPC connection is terminated.

The API request dispatching of the CodeChecker server has a **`TaskManager`** instance which should be passed to the API handler implementation, if not already available.
Then, you can use this _`TaskManager`_ object to perform the necessary actions to enqueue the execution of a task:


```py3
from pathlib import Path
from ..profiler import timeit
from ..task_executors.task_manager import TaskManager
from .common import exc_to_thrift_reqfail

class MyThriftEndpointHandler:
    def __init__(self, task_manager: TaskManager):
        self._task_manager = task_manager

    @exc_to_thrift_reqfail
    @timeit
    def apiRequestThatResultsInATask(self, arg1, arg2, large_arg: str,  ...) -> str:  # Return the task token!
        # Conformance checks and assertions on the input's validity.
        if invalid_input(arg1, arg2):
            raise ValueError("Bad request!")

        # Allocate the task token.
        tok: str = self._task_manager.allocate_task_record(
            # The task's "Kind": a simple string identifier which should NOT
            # depend on user input!
            # Used in filters and to quickly identify the "type" for a task
            # record.
            "MyThriftEndpointHandler::apiRequestThatResultsInATask()",

            # The task's "Summary": an arbitrary string that is used visually
            # to describe the executing task. This can be anything, even
            # spliced together from user input.
            # This is not used in the filters.
            "This is a task that was spawned from the API!",

            # The task's "User": the name of the user who is the actor which
            # caused the execution of the task.
            # The status of the task may only be queried by the relevant actor,
            # a PRODUCT_ADMIN (if the task is associated with a product) or
            # SUPERUSERs.
            "user",

            # If the task is associated with a product, pass the ORM `Product`
            # object here. Otherwise, pass `None`.
            current_product_obj or None)

        # Large inputs to the task **MUST** be passed through the file system
        # in order not to crash the server.
        # **If** the task needs large inputs, they must go into a temporary
        # directory appropriately created by the task manager.
        data_dir: Path = self._task_manager.create_task_data(tok)

        # Create the files under `data_dir` ...
        with open(data_dir / "large.txt", 'w') as f:
            f.write(large_arg)

        # Instantiate the `MyTask` class (see later) which contains the
        # actual business logic of the task.
        #
        # Small input fields that are of trivial serialisable Python types
        # (scalars, string, etc., but not file descriptors or network
        # connections) can be passed directly to the task object's constructor.
        task = MyTask(token, data_dir, arg1, arg2)

        # Enqueue the task, at which point it may start immediately executing,
        # depending on server load.
        self._task_manager.push_task(task)

        return tok
```


### "Background" logic

The business logic of tasks are implemented by subclassing the _`AbstractTask`_ class and providing an appropriate constructor and overriding the **`_implementation()`** method.

1. Once a _`Task`_ instance is pushed into the server's task queue by _`TaskManager::push_task()`_, one of the background workers of the server will awaken and pop the task from the queue. The size of the queue is limited, hence why only **small** arguments may be present in the state of the _`Task`_ object!
2. This popped object is reconstructed by the standard Python library _`pickle`_, hence why only **trivial** scalar-like objects may be present in the state of the _`Task`_ object!
3. The executor starts running the custom **`_implementation()`** method, after setting the task's status to _`RUNNING`_.
4. The implementation does its thing, periodically calling _`task_manager.heartbeat()`_ to update the progress timestamp of the task, and, if appropriate, checking with _`task_manager.should_cancel()`_ whether the admins requested the task to cancel or the server is shutting down.
5. If _`should_cancel()`_ returned `True`, the task does some appropriate clean-up, and exits by raising the special _`TaskCancelHonoured`_ exception, indicating that it responded to the request. (At this point, the status becomes either _`CANCELLED`_ or _`DROPPED`_, depending on the circumstances of the service.)
6. Otherwise, or if the task is for some reason not cancellable without causing damage, the task executes its logic.
7. If the task's _`_implementation()`_ method exits cleanly, it reaches the _`COMPLETED`_ status; otherwise, if any exception escapes from the _`_implementation()`_ method, the task becomes _`FAILED`_.

**Caution!** Tasks, executing in a separate background process part of the many processes spawned by a CodeChecker server, no longer have the ability to synchronously communicate with the user!
This also includes the lack of ability to "return" a value: tasks **only exercise side-effects**, but do not calculate a "result".


```py3
from ..task_executors.abstract_task import AbstractTask
from ..task_executors.task_manager import TaskManager

class MyTask(AbstractTask):
    def __init__(self, token: str, data_dir: Path, arg1, arg2):  # Note: No large_arg!
        # If the task does not use a temporary data directory, `data_dir` can
        # be omitted, and `None` may be passed instead!
        super().__init__(token, data_dir)
        self.arg1 = arg1
        self.arg2 = arg2

    def _implementation(self, tm: TaskManager) -> None:  # Tasks do not have a result value!
        # First, obtain the rest of the input (e.g., `large_arg`),
        # if any is needed.
        with open(self.data_path / "large.txt", 'r') as f:
            large_arg: str = f.read()

        # Exceptions raised above, e.g., the lack of the file, automatically
        # turn the task into the FAILED state.

        # Let's assume the task does something in an iteration...
        for i in range(0, int(self.arg1) + int(self.arg2)):
            tm.heartbeat()  # Indicate some progress ...
            element = large_arg.split('\n')[i]

            if tm.should_cancel(self):
                # A shutdown was requested of the running task.

                # Perform some cleanup logic ...

                # Maybe have some customised log?
                tm.add_comment(self,
                               # The body of the comment.
                               "Oh shit, we are shutting down ...!\n"
                               f"But only processed {i + 1} entries!",

                               # The actor entity associated with the comment.
                               "SYSTEM?")

                raise TaskCancelHonoured(self)

            # Actually process the step ...
            foo(element)
```

Client-side handling
--------------------

In a client, call the task-generating API endpoint normally.
It should return a `str`, the **`token`** identifier of the task.

This _token_ can be awaited (polled) programmatically using a library function:


```py3
from codechecker_client import client as libclient
from codechecker_client.task_client import await_task_termination

def main(...) -> int:
    client = setup_client(server_url or product_url)
    tok: str = client.apiRequestThatResultsInATask(16, 32, large_arg_str)

    prot, host, port = split_server_url(server_url)
    task_client = libclient.setup_task_client(prot, host, port)
    status: str = await_task_termination(LOG, tok,
                                         task_api_client=task_client)

    if status == "COMPLETED":
        return 0
    LOG.error("The execution of the task failed!\n%s",
              task_client.getTaskInfo(tok).comments)
    return 1
```

In simpler wrapper scripts, alternatively,
`CodeChecker cmd serverside-tasks --token TOK --await` may be used to block
execution until a task terminates (one way or another).
