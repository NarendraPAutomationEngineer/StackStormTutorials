# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import abc
import copy
import six
from six.moves import queue
import unittest

from orquesta import conducting
from orquesta import events
from orquesta.expressions import base as expr_base
from orquesta.specs import loader as spec_loader
from orquesta import statuses
from orquesta.tests.fixtures import loader as fixture_loader
from orquesta.utils import plugin as plugin_util
from orquesta.utils import specs as spec_util


@six.add_metaclass(abc.ABCMeta)
class ExpressionEvaluatorTest(unittest.TestCase):
    language = None
    evaluator = None

    @classmethod
    def setUpClass(cls):
        cls.evaluator = plugin_util.get_module('orquesta.expressions.evaluators', cls.language)


@six.add_metaclass(abc.ABCMeta)
class ExpressionFacadeEvaluatorTest(unittest.TestCase):

    def validate(self, expr):
        return expr_base.validate(expr).get('errors', [])


@six.add_metaclass(abc.ABCMeta)
class WorkflowGraphTest(unittest.TestCase):

    def _zip_wf_graph_meta(self, wf_graph_json):
        wf_graph_json['adjacency'] = [
            sorted(link, key=lambda x: x['id']) if link else link
            for link in wf_graph_json['adjacency']
        ]

        wf_graph_meta = sorted(
            zip(wf_graph_json['nodes'], wf_graph_json['adjacency']),
            key=lambda x: x[0]['id']
        )

        return wf_graph_meta

    def assert_graph_equal(self, wf_graph, expected_wf_graph):
        wf_graph_json = wf_graph.serialize()
        wf_graph_meta = self._zip_wf_graph_meta(wf_graph_json)
        expected_wf_graph_meta = self._zip_wf_graph_meta(expected_wf_graph)

        self.assertListEqual(wf_graph_meta, expected_wf_graph_meta)

        wf_graph_attrs = sorted(wf_graph_json['graph'], key=lambda x: x[0])
        expected_wf_graph_attrs = sorted(expected_wf_graph['graph'], key=lambda x: x[0])

        self.assertListEqual(wf_graph_attrs, expected_wf_graph_attrs)


class WorkflowSpecTest(unittest.TestCase):
    spec_module_name = 'mock'

    def __init__(self, *args, **kwargs):
        super(WorkflowSpecTest, self).__init__(*args, **kwargs)
        self.maxDiff = None

    def get_fixture_path(self, wf_name):
        return self.spec_module_name + '/' + wf_name + '.yaml'

    def get_wf_def(self, wf_name, raw=False):
        return fixture_loader.get_fixture_content(
            self.get_fixture_path(wf_name),
            'workflows',
            raw=raw
        )

    def get_wf_spec(self, wf_name):
        wf_def = self.get_wf_def(wf_name)
        wf_spec = spec_util.instantiate(self.spec_module_name, wf_def)
        return wf_spec

    def instantiate(self, wf_def):
        return spec_util.instantiate(self.spec_module_name, wf_def)

    def assert_spec_inspection(self, wf_name, errors=None):
        wf_spec = self.get_wf_spec(wf_name)

        self.assertDictEqual(wf_spec.inspect(), errors or {})


@six.add_metaclass(abc.ABCMeta)
class WorkflowComposerTest(WorkflowGraphTest, WorkflowSpecTest):
    composer = None

    @classmethod
    def setUpClass(cls):
        WorkflowGraphTest.setUpClass()
        WorkflowSpecTest.setUpClass()

        cls.composer = plugin_util.get_module('orquesta.composers', cls.spec_module_name)
        cls.spec_module = spec_loader.get_spec_module(cls.spec_module_name)
        cls.wf_spec_type = cls.spec_module.WorkflowSpec

    def compose_wf_graph(self, wf_name):
        wf_def = self.get_wf_def(wf_name)
        wf_spec = self.spec_module.instantiate(wf_def)

        return self.composer._compose_wf_graph(wf_spec)

    def assert_compose_to_wf_graph(self, wf_name, expected_wf_graph):
        wf_graph = self.compose_wf_graph(wf_name)

        self.assert_graph_equal(wf_graph, expected_wf_graph)

    def compose_wf_ex_graph(self, wf_name):
        wf_def = self.get_wf_def(wf_name)
        wf_spec = self.spec_module.instantiate(wf_def)

        return self.composer.compose(wf_spec)

    def assert_compose_to_wf_ex_graph(self, wf_name, expected_wf_ex_graph):
        wf_ex_graph = self.compose_wf_ex_graph(wf_name)

        self.assert_graph_equal(wf_ex_graph, expected_wf_ex_graph)


@six.add_metaclass(abc.ABCMeta)
class WorkflowConductorTest(WorkflowComposerTest):

    def format_task_item(self, task_id, route, ctx, spec, actions=None, delay=None,
                         items_count=None, items_concurrency=None):

        if not actions and items_count is None:
            actions = [{'action': spec.action, 'input': spec.input}]

        task = {
            'id': task_id,
            'route': route,
            'ctx': ctx,
            'spec': spec,
            'actions': actions or []
        }

        if delay:
            task['delay'] = delay

        if items_count is not None:
            task['items_count'] = items_count
            task['concurrency'] = items_concurrency

        return task

    def forward_task_statuses(self, conductor, task_id, statuses, ctxs=None, results=None, route=0):
        for status, ctx, result in six.moves.zip_longest(statuses, ctxs or [], results or []):
            ac_ex_event = events.ActionExecutionEvent(status)

            if result:
                ac_ex_event.result = result

            if ctx:
                ac_ex_event.context = ctx

            conductor.update_task_state(task_id, route, ac_ex_event)

    # The conductor.get_next_tasks make copies of the task specs and render expressions
    # in the task action and task input. So comparing the task specs will not match. In
    # order to match in unit tests. This method is used to serialize the task specs and
    # compare the lists.
    def assert_task_list(self, conductor, actual, expected):
        actual_copy = copy.deepcopy(actual)
        expected_copy = copy.deepcopy(expected)

        for task in actual_copy:
            task['spec'] = task['spec'].serialize()

            for staged_task in task['ctx']['__state']['staged']:
                if 'items' in staged_task:
                    del staged_task['items']

        for task in expected_copy:
            task['ctx']['__current_task'] = {'id': task['id'], 'route': task['route']}
            task['ctx']['__state'] = conductor.workflow_state.serialize()
            task['spec'] = task['spec'].serialize()

            for staged_task in task['ctx']['__state']['staged']:
                if 'items' in staged_task:
                    del staged_task['items']

        self.assertListEqual(actual_copy, expected_copy)

    def assert_next_task(self, conductor, task_id=None, ctx=None, route=0, has_next_task=True):
        expected_tasks = []

        if has_next_task:
            task_spec = conductor.spec.tasks.get_task(task_id)
            expected_tasks = [self.format_task_item(task_id, route, ctx, task_spec)]

        self.assert_task_list(conductor, conductor.get_next_tasks(), expected_tasks)

    def assert_next_tasks(self, conductor, task_ids=None, ctxs=None, routes=None):
        expected_tasks = []

        for task_id, ctx, route in zip(task_ids, ctxs, routes):
            task_spec = conductor.spec.tasks.get_task(task_id)
            expected_tasks.append(self.format_task_item(task_id, route, ctx, task_spec))

        self.assert_task_list(conductor, conductor.get_next_tasks(), expected_tasks)

    def assert_conducting_sequences(self, wf_name, expected_task_seq, expected_routes=None,
                                    inputs=None, mock_statuses=None, mock_results=None,
                                    expected_workflow_status=None, expected_output=None,
                                    expected_term_tasks=None):

        if not expected_routes:
            expected_routes = [[]]

        if inputs is None:
            inputs = {}

        wf_def = self.get_wf_def(wf_name)
        wf_spec = self.spec_module.instantiate(wf_def)
        conductor = conducting.WorkflowConductor(wf_spec, inputs=inputs)
        conductor.request_workflow_status(statuses.RUNNING)

        run_q = queue.Queue()
        status_q = queue.Queue()
        result_q = queue.Queue()

        if mock_statuses:
            for item in mock_statuses:
                status_q.put(item)

        if mock_results:
            for item in mock_results:
                result_q.put(item)

        # Get start tasks and being conducting workflow.
        for task in conductor.get_next_tasks():
            run_q.put(task)

        # Serialize workflow conductor to mock async execution.
        wf_conducting_state = conductor.serialize()

        # Process until there are not more tasks in queue.
        while not run_q.empty():
            # Deserialize workflow conductor to mock async execution.
            conductor = conducting.WorkflowConductor.deserialize(wf_conducting_state)

            # Process all the tasks in the run queue.
            while not run_q.empty():
                current_task = run_q.get()
                current_task_id = current_task['id']
                current_task_route = current_task['route']

                # Set task status to running.
                ac_ex_event = events.ActionExecutionEvent(statuses.RUNNING)
                conductor.update_task_state(current_task_id, current_task_route, ac_ex_event)

                # Mock completion of the task.
                status = status_q.get() if not status_q.empty() else statuses.SUCCEEDED
                result = result_q.get() if not result_q.empty() else None

                ac_ex_event = events.ActionExecutionEvent(status, result=result)
                conductor.update_task_state(current_task_id, current_task_route, ac_ex_event)

            # Identify the next set of tasks.
            for next_task in conductor.get_next_tasks():
                run_q.put(next_task)

            # Serialize workflow execution graph to mock async execution.
            wf_conducting_state = conductor.serialize()

        actual_task_seq = [
            (entry['id'], entry['route'])
            for entry in conductor.workflow_state.sequence
        ]

        expected_task_seq = [
            task_seq if isinstance(task_seq, tuple) else (task_seq, 0)
            for task_seq in expected_task_seq
        ]

        self.assertListEqual(actual_task_seq, expected_task_seq)
        self.assertListEqual(conductor.workflow_state.routes, expected_routes)

        if expected_workflow_status is None:
            expected_workflow_status = statuses.SUCCEEDED

        self.assertEqual(conductor.get_workflow_status(), expected_workflow_status)

        if expected_output is not None:
            self.assertDictEqual(conductor.get_workflow_output(), expected_output)

        if expected_term_tasks:
            expected_term_tasks = [
                (task, 0) if not isinstance(task, tuple) else task
                for task in expected_term_tasks
            ]

            term_tasks = conductor.workflow_state.get_terminal_tasks()
            actual_term_tasks = [(task['id'], task['route']) for task in term_tasks]
            self.assertListEqual(actual_term_tasks, expected_term_tasks)

    def assert_workflow_status(self, wf_name, mock_flow, expected_wf_statuses, conductor=None):
        if not conductor:
            wf_def = self.get_wf_def(wf_name)
            wf_spec = self.spec_module.instantiate(wf_def)
            conductor = conducting.WorkflowConductor(wf_spec)
            conductor.request_workflow_status(statuses.RUNNING)

        for _entry, expected_wf_status in zip(mock_flow, expected_wf_statuses):
            task_id = _entry['id']
            task_status = _entry['status']

            self.forward_task_statuses(conductor, task_id, [task_status])

            err_ctx = (
                'Workflow status "%s" is not the expected status "%s". '
                'Updated task "%s" with status "%s".' %
                (conductor.get_workflow_status(), expected_wf_status, task_id, task_status)
            )

            self.assertEqual(conductor.get_workflow_status(), expected_wf_status, err_ctx)

        return conductor


class WorkflowConductorWithItemsTest(WorkflowConductorTest):

    def assert_task_items(self, conductor, task_id, task_route, task_ctx, items, action_specs,
                          mock_ac_ex_statuses, expected_task_statuses, expected_workflow_statuses,
                          concurrency=None):

        # Set up test cases.
        tests = list(zip(mock_ac_ex_statuses, expected_task_statuses, expected_workflow_statuses))

        # Verify the first set of action executions.
        expected_task = self.format_task_item(
            task_id,
            task_route,
            task_ctx,
            conductor.spec.tasks.get_task(task_id),
            actions=action_specs[0:concurrency],
            items_count=len(items),
            items_concurrency=concurrency
        )

        expected_tasks = [expected_task]
        actual_tasks = conductor.get_next_tasks()
        self.assert_task_list(conductor, actual_tasks, expected_tasks)

        # If items is an empty list, then mark the task as running.
        if len(items) == 0:
            ac_ex_event = events.ActionExecutionEvent(statuses.RUNNING)
            conductor.update_task_state(task_id, task_route, ac_ex_event)
        else:
            # Mark the first set of action executions as running.
            for i in range(0, min(len(tests), concurrency or len(items))):
                context = {'item_id': i}
                ac_ex_event = events.ActionExecutionEvent(statuses.RUNNING, context=context)
                conductor.update_task_state(task_id, task_route, ac_ex_event)

        # Ensure the actions listed is accurate when getting next tasks again.
        expected_tasks = []
        capacity = len(items)
        next_item_id = len(tests)
        next_action_specs = []

        if concurrency is not None and concurrency > 0:
            items_running = min(len(tests), concurrency or len(items))
            capacity = concurrency - items_running

        if capacity > 0 and next_item_id < len(items):
            next_action_specs = action_specs[next_item_id:next_item_id + capacity]

        if next_action_specs or len(items) == 0:
            expected_task = self.format_task_item(
                task_id,
                task_route,
                task_ctx,
                conductor.spec.tasks.get_task(task_id),
                actions=next_action_specs,
                items_count=len(items),
                items_concurrency=concurrency
            )

            expected_tasks = [expected_task]

        actual_tasks = conductor.get_next_tasks()
        self.assert_task_list(conductor, actual_tasks, expected_tasks)

        # If items is an empty list, complete the task.
        if len(items) == 0:
            ac_ex_event = events.ActionExecutionEvent(statuses.SUCCEEDED)
            conductor.update_task_state(task_id, task_route, ac_ex_event)

        # Mock the action execution for each item.
        for i in range(0, len(tests)):
            context = {'item_id': i}
            result = items[i]
            ac_ex_status = tests[i][0]
            ac_ex_event = events.ActionExecutionEvent(ac_ex_status, result, context)
            conductor.update_task_state(task_id, task_route, ac_ex_event)

            expected_task_status = tests[i][1]
            actual_task_status = conductor.get_task_state_entry(task_id, task_route)['status']

            error_message = (
                'Task execution status "%s" does not match "%s" for item %s.' %
                (actual_task_status, expected_task_status, i)
            )

            self.assertEqual(actual_task_status, expected_task_status, error_message)

            expected_workflow_status = tests[i][2]
            actual_workflow_status = conductor.get_workflow_status()

            error_message = (
                'Workflow execution status "%s" does not match "%s" after item %s update.' %
                (actual_workflow_status, expected_workflow_status, i)
            )

            self.assertEqual(actual_workflow_status, expected_workflow_status, error_message)

            # Process next set of action executions only if there are more test cases.
            if i >= len(tests) - 2 or concurrency is None:
                continue

            item_id = i + concurrency
            expected_tasks = []

            if item_id < len(items):
                expected_task = self.format_task_item(
                    task_id,
                    task_route,
                    task_ctx,
                    conductor.spec.tasks.get_task(task_id),
                    actions=action_specs[item_id:item_id + 1],
                    items_count=len(items),
                    items_concurrency=concurrency
                )

                expected_tasks = [expected_task]

            actual_tasks = conductor.get_next_tasks()
            self.assert_task_list(conductor, actual_tasks, expected_tasks)

            for task in actual_tasks:
                task_id = task['id']

                for action in task['actions']:
                    ctx = {'item_id': action['item_id']}
                    ac_ex_event = events.ActionExecutionEvent(statuses.RUNNING, context=ctx)
                    conductor.update_task_state(task_id, task_route, ac_ex_event)
