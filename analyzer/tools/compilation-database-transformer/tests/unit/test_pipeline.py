# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""
This module tests the Pipeline and JsonPipeline classes, which are used
to implement a sequence of transformations on input data.
"""

import unittest

from compilation_database_transformer.pipeline import Pipeline


class PipelineTestCase(unittest.TestCase):
    """ Test the pipeline building and evaluation of pipeline steps. """

    def test_empty_pipeline_with_builtin(self):
        """Test an empty pipeline for equality with builtin type."""

        self.assertEqual(Pipeline().feed(0), 0)

    def test_empty_pipeline_with_user_defined(self):
        """Test an empty pipeline for equality with user defined type."""
        class A:
            pass

        a = A()

        self.assertEqual(Pipeline().feed(a), a)

    def test_empty_pipeline_with_user_defined_is_same(self):
        """Test an empty pipeline for referential equality with user defined
        type."""
        class A:
            pass

        a = A()

        self.assertIs(Pipeline().feed(a), a)

    def test_single_transform(self):
        """Test single transform, by providing a transform function at
        construction time."""
        pipeline = Pipeline([str.upper])

        self.assertEqual(pipeline.feed('input'), 'INPUT')

    def test_single_transform_building(self):
        """Test single transform, by providing a transform function via
        a builder method."""
        pipeline = Pipeline().append_transform(str.upper)

        self.assertEqual(pipeline.feed('input'), 'INPUT')

    def test_single_map_empty_list(self):
        """Test single map with an empty list as input."""
        pipeline = Pipeline().append_map(str.upper)

        self.assertEqual(pipeline.feed([]), [])

    def test_single_map_non_empty(self):
        """Test single map with a non-empty list as input."""
        pipeline = Pipeline().append_map(str.upper)

        self.assertEqual(pipeline.feed(['input1', 'input2']),
                         ['INPUT1', 'INPUT2'])

    def test_prepend_transform(self):
        """Test pipleline building with prepend transform opeartion."""
        pipeline = Pipeline() \
            .prepend_transform(lambda x: x * 2) \
            .prepend_transform(lambda x: x + 10)

        # (10 + 10) * 2
        self.assertEqual(pipeline.feed(10), 40)

    def test_prepend_map(self):
        """Test pipleline building with prepend map opeartion."""
        pipeline = Pipeline() \
            .prepend_map(lambda x: x * 2) \
            .prepend_map(lambda x: x + 10)

        self.assertEqual(pipeline.feed([10, 20]), [40, 60])

    def test_append_pipeline(self):
        """Test append pipe opeartion."""
        pipeline = Pipeline()
        pipeline.append_transform(lambda x: x * 2)

        pipeline2 = Pipeline()
        pipeline2.append_transform(lambda x: x + 10)

        pipeline.append_pipe(pipeline2)

        # (10 * 2) + 10
        self.assertEqual(pipeline.feed(10), 30)

    def test_append_pipeline2(self):
        """Test append pipe opeartion."""
        pipeline = Pipeline().append_transform(lambda x: x * 2)

        pipeline2 = Pipeline() \
            .append_transform(lambda x: x + 10) \
            .append_transform(lambda x: x / 2)

        pipeline.append_pipe(pipeline2)

        # ((10 * 2) + 10) / 2
        self.assertEqual(pipeline.feed(10), 15)

    def test_prepend_pipeline(self):
        """Test prepend pipe opeartion."""
        pipeline = Pipeline().append_transform(lambda x: x * 2)

        pipeline2 = Pipeline() \
            .append_transform(lambda x: x + 10) \
            .append_transform(lambda x: x / 2)

        pipeline.prepend_pipe(pipeline2)

        # ((10 + 10) / 2) * 2
        self.assertEqual(pipeline.feed(10), 20)

    def test_append_pipeline_map(self):
        """Test append pipe map opeartion."""
        pipeline = Pipeline().append_transform(lambda x: x * 2)

        pipeline2 = Pipeline() \
            .append_transform(lambda x: x + 10) \
            .append_transform(lambda x: x / 2)

        pipeline.prepend_pipe(pipeline2)

        # ((10 + 10) / 2) * 2
        self.assertEqual(pipeline.feed(10), 20)

    def test_append_pipeline_map2(self):
        """Test append pipe map opeartion."""
        pipeline = Pipeline().append_map(lambda x: x * 2)

        pipeline2 = Pipeline() \
            .append_transform(lambda x: x + 10) \
            .append_transform(lambda x: x / 2)

        pipeline.append_pipe_map(pipeline2)

        # for each element ((x * 2) + 10) / 2
        self.assertEqual(pipeline.feed([10, 20]), [15, 25])

    def test_prepend_pipeline_map(self):
        """Test prepend pipe map opeartion."""
        pipeline = Pipeline().append_map(lambda x: x * 2)

        pipeline2 = Pipeline() \
            .append_transform(lambda x: x + 10) \
            .append_transform(lambda x: x / 2)

        pipeline.prepend_pipe_map(pipeline2)

        # for each element ((x + 10) / 2) * 2
        self.assertEqual(pipeline.feed([10, 20]), [20, 30])

    def test_flatten(self):
        """Test flatten opeartion."""
        pipeline = Pipeline() \
            .append_transform(lambda x: x * 3)

        self.assertEqual(pipeline.feed([10]), [10, 10, 10])

        pipeline.append_map(lambda x: [x])

        self.assertEqual(pipeline.feed([10]), [[10], [10], [10]])

        pipeline2 = Pipeline() \
            .append_map(lambda x: x + 20) \
            .append_map(lambda x: x / 2)

        pipeline.append_pipe_map(pipeline2)

        self.assertEqual(pipeline.feed([10]), [[15], [15], [15]])

        pipeline.flatten()

        self.assertEqual(pipeline.feed([10]), [15, 15, 15])

    def test_prepend_flatten(self):
        """Test prepend flatten opeartion."""

        pipeline = Pipeline() \
            .append_transform(lambda x: x * 3)

        self.assertEqual(pipeline.feed([[10]]), [[10], [10], [10]])

        pipeline.pre_flatten()

        self.assertEqual(pipeline.feed([[10]]), [10, 10, 10])

        pipeline2 = Pipeline() \
            .append_transform(lambda x: x + 20) \
            .append_transform(lambda x: x / 2)

        pipeline.append_pipe_map(pipeline2)

        self.assertEqual(pipeline.feed([[10]]), [15, 15, 15])
