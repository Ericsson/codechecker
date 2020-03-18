import collections
import functools
import json
from itertools import chain
from typing import Any, Callable, IO, List, Iterable


def inv_compose(*fs: [Callable]):
    """
    Composition of functions. Note that contrary to the mathematical notation
    the function returned by inv_compose(f, g) executes f first, and then g.
    """
    return functools.reduce(
        lambda f1, f2: lambda x: f2(f1(x)), fs, lambda x: x)


def eager_map(f: Callable):
    """
    Force the evaluation of generator expressions after using map.
    Eager mapping is desirable because it improves the readability of the
    Pipeline definitions.
    """
    return inv_compose(functools.partial(map, f), list)


class Pipeline:
    """
    A series of functions, intended to be executed sequentially,
    passing their results on the next step with each execution step.
    """

    def __init__(self, pipeline: Iterable[Callable] = None):
        self.pipeline = collections.deque()
        if pipeline is not None:
            self.pipeline.extend(pipeline)

    def prepend_transform(self, transform_func: Callable):
        """
        Prepend an action, which feeds the input data in the pipeline to the
        transform_func.
        """
        self.pipeline.appendleft(transform_func)
        return self

    def append_transform(self, transform_func: Callable):
        """
        Append an action, which feeds the data at this point in the pipeline
        to the transform_func.
        """
        self.pipeline.append(transform_func)
        return self

    def prepend_map(self, mapping_func: Callable):
        """
        Prepend an action, which maps the input data in the pipeline to the
        mapping_func.
        """
        self.pipeline.appendleft(eager_map(mapping_func))
        return self

    def append_map(self, mapping_func: Callable):
        """
        Append an action, which maps the data at this point in the pipeline
        to the mapping_func.
        """
        self.pipeline.append(eager_map(mapping_func))
        return self

    def prepend_pipe(self, pipe: 'Pipeline'):
        """
        Prepend an action, which feeds the input data in the pipeline to the
        first step of the pipe given.
        """
        self.prepend_transform(pipe.feed)
        return self

    def append_pipe(self, pipe: 'Pipeline'):
        """
        Append an action, which feeds the data at this point in the pipeline
        to the first step of the pipe given.
        """
        self.append_transform(pipe.feed)
        return self

    def prepend_pipe_map(self, pipe: 'Pipeline'):
        """
        Prepend an action, which maps the input data in the pipeline to the
        first step of the pipe given.
        """
        self.prepend_map(pipe.feed)
        return self

    def append_pipe_map(self, pipe: 'Pipeline'):
        """
        Append an action, which maps the data at this point in the pipeline
        to the first step of the pipe given.
        """
        self.append_map(pipe.feed)
        return self

    def pre_flatten(self):
        """
        Prepend an action, which transforms doubly nested lists only one
        level deep.
        """
        self.prepend_transform(inv_compose(
            chain.from_iterable,
            list
        ))
        return self

    def flatten(self):
        """
        Append an action, which transforms doubly nested lists only one
        level deep.
        """
        self.append_transform(inv_compose(
            chain.from_iterable,
            list
        ))
        return self

    def feed(self, source: Any):
        """
        Execute the steps of the pipeline by feeding input into the first one,
        and executing every step using the intermediate results.
        """
        for pipeline_step in self.pipeline:
            source = pipeline_step(source)
        return source


class JsonPipeline(Pipeline):
    """
    JsonPipeline has a fixed prefix step for reading a list of JSON
    IO-sources, and fixed postfix step for serializing the result in JSON
    format.
    """

    def __init__(self, output: IO, pipeline: List[Callable] = None):
        super().__init__(pipeline)
        self.prepend_map(json.load)
        self.output = output

    def feed(self, json_sources: List[IO]):
        """
        Using the provided inputs, process every step in the pipeline, and
        return the results.
        """

        # Write the results in a JSON format.
        self.append_transform(
            lambda results: json.dump(results, self.output, indent=2))
        return super().feed(json_sources)
