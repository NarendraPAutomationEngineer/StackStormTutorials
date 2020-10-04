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

from orquesta import conducting
from orquesta.specs import native as native_specs
from orquesta import statuses
from orquesta.tests.unit import base as test_base


class WorkflowConductorWithItemsCancelTest(test_base.WorkflowConductorWithItemsTest):

    def test_cancel_item_list_processed(self):
        wf_def = """
        version: 1.0

        vars:
          - xs:
              - fee
              - fi
              - fo
              - fum

        tasks:
          task1:
            with: <% ctx(xs) %>
            action: core.echo message=<% item() %>
            next:
              - publish:
                  - items: <% result() %>

        output:
          - items: <% ctx(items) %>
        """

        spec = native_specs.WorkflowSpec(wf_def)
        self.assertDictEqual(spec.inspect(), {})

        conductor = conducting.WorkflowConductor(spec)
        conductor.request_workflow_status(statuses.RUNNING)

        # Mock the action execution for each item and assert expected task statuses.
        task_route = 0
        task_name = 'task1'
        task_ctx = {'xs': ['fee', 'fi', 'fo', 'fum']}

        task_action_specs = [
            {'action': 'core.echo', 'input': {'message': 'fee'}, 'item_id': 0},
            {'action': 'core.echo', 'input': {'message': 'fi'}, 'item_id': 1},
            {'action': 'core.echo', 'input': {'message': 'fo'}, 'item_id': 2},
            {'action': 'core.echo', 'input': {'message': 'fum'}, 'item_id': 3},
        ]

        mock_ac_ex_statuses = [
            statuses.SUCCEEDED,
            statuses.CANCELED,
            statuses.SUCCEEDED,
            statuses.SUCCEEDED
        ]

        expected_task_statuses = [
            statuses.RUNNING,
            statuses.CANCELING,
            statuses.CANCELING,
            statuses.CANCELED
        ]

        expected_workflow_statuses = [
            statuses.RUNNING,
            statuses.CANCELING,
            statuses.CANCELING,
            statuses.CANCELED
        ]

        self.assert_task_items(
            conductor,
            task_name,
            task_route,
            task_ctx,
            task_ctx['xs'],
            task_action_specs,
            mock_ac_ex_statuses,
            expected_task_statuses,
            expected_workflow_statuses
        )

        # Assert the task is removed from staging.
        self.assertIsNone(conductor.workflow_state.get_staged_task(task_name, task_route))

        # Assert the workflow succeeded.
        self.assertEqual(conductor.get_workflow_status(), statuses.CANCELED)

    def test_cancel_item_list_incomplete(self):
        wf_def = """
        version: 1.0

        vars:
          - xs:
              - fee
              - fi
              - fo
              - fum

        tasks:
          task1:
            with: <% ctx(xs) %>
            action: core.echo message=<% item() %>
            next:
              - publish:
                  - items: <% result() %>

        output:
          - items: <% ctx(items) %>
        """

        spec = native_specs.WorkflowSpec(wf_def)
        self.assertDictEqual(spec.inspect(), {})

        conductor = conducting.WorkflowConductor(spec)
        conductor.request_workflow_status(statuses.RUNNING)

        # Mock the action execution for each item and assert expected task statuses.
        task_route = 0
        task_name = 'task1'
        task_ctx = {'xs': ['fee', 'fi', 'fo', 'fum']}

        task_action_specs = [
            {'action': 'core.echo', 'input': {'message': 'fee'}, 'item_id': 0},
            {'action': 'core.echo', 'input': {'message': 'fi'}, 'item_id': 1},
            {'action': 'core.echo', 'input': {'message': 'fo'}, 'item_id': 2},
            {'action': 'core.echo', 'input': {'message': 'fum'}, 'item_id': 3},
        ]

        mock_ac_ex_statuses = [statuses.SUCCEEDED, statuses.CANCELED, statuses.SUCCEEDED]
        expected_task_statuses = [statuses.RUNNING, statuses.CANCELING, statuses.CANCELED]
        expected_workflow_statuses = [statuses.RUNNING, statuses.CANCELING, statuses.CANCELED]

        self.assert_task_items(
            conductor,
            task_name,
            task_route,
            task_ctx,
            task_ctx['xs'],
            task_action_specs,
            mock_ac_ex_statuses,
            expected_task_statuses,
            expected_workflow_statuses
        )

        # Assert the task is removed from staging.
        self.assertIsNone(conductor.workflow_state.get_staged_task(task_name, task_route))

        # Assert the workflow is canceled.
        self.assertEqual(conductor.get_workflow_status(), statuses.CANCELED)

    def test_cancel_workflow_using_canceling_status_with_items_active(self):
        wf_def = """
        version: 1.0

        vars:
          - xs:
              - fee
              - fi
              - fo
              - fum

        tasks:
          task1:
            with: <% ctx(xs) %>
            action: core.echo message=<% item() %>
            next:
              - publish:
                  - items: <% result() %>

        output:
          - items: <% ctx(items) %>
        """

        spec = native_specs.WorkflowSpec(wf_def)
        self.assertDictEqual(spec.inspect(), {})

        conductor = conducting.WorkflowConductor(spec)
        conductor.request_workflow_status(statuses.RUNNING)

        # Mock the action execution for each item and assert expected task statuses.
        task_route = 0
        task_name = 'task1'
        task_ctx = {'xs': ['fee', 'fi', 'fo', 'fum']}

        task_action_specs = [
            {'action': 'core.echo', 'input': {'message': 'fee'}, 'item_id': 0},
            {'action': 'core.echo', 'input': {'message': 'fi'}, 'item_id': 1},
            {'action': 'core.echo', 'input': {'message': 'fo'}, 'item_id': 2},
            {'action': 'core.echo', 'input': {'message': 'fum'}, 'item_id': 3},
        ]

        # Verify the set of action executions.
        expected_task = self.format_task_item(
            task_name,
            task_route,
            task_ctx,
            conductor.spec.tasks.get_task(task_name),
            actions=task_action_specs,
            items_count=len(task_ctx['xs'])
        )

        expected_tasks = [expected_task]
        actual_tasks = conductor.get_next_tasks()
        self.assert_task_list(conductor, actual_tasks, expected_tasks)

        # Set the items to running status.
        for i in range(0, len(task_ctx['xs'])):
            context = {'item_id': i}
            self.forward_task_statuses(conductor, task_name, [statuses.RUNNING], [context])

        # Assert that the task is running.
        actual_task_status = conductor.workflow_state.get_task(task_name, task_route)['status']
        self.assertEqual(actual_task_status, statuses.RUNNING)

        # Cancel the workflow.
        conductor.request_workflow_status(statuses.CANCELING)
        self.assertEqual(conductor.get_workflow_status(), statuses.CANCELING)
        actual_task_status = conductor.workflow_state.get_task(task_name, task_route)['status']
        self.assertEqual(actual_task_status, statuses.CANCELING)

        # Complete the items.
        for i in range(0, len(task_ctx['xs'])):
            contexts = [{'item_id': i}]
            results = [task_ctx['xs'][i]]
            status_changes = [statuses.SUCCEEDED]
            self.forward_task_statuses(conductor, task_name, status_changes, contexts, results)

        # Assert the task is completed and workflow is canceled.
        actual_task_status = conductor.workflow_state.get_task(task_name, task_route)['status']
        self.assertEqual(actual_task_status, statuses.SUCCEEDED)
        self.assertEqual(conductor.get_workflow_status(), statuses.CANCELED)

    def test_cancel_workflow_using_canceled_status_with_items_active(self):
        wf_def = """
        version: 1.0

        vars:
          - xs:
              - fee
              - fi
              - fo
              - fum

        tasks:
          task1:
            with: <% ctx(xs) %>
            action: core.echo message=<% item() %>
            next:
              - publish:
                  - items: <% result() %>

        output:
          - items: <% ctx(items) %>
        """

        spec = native_specs.WorkflowSpec(wf_def)
        self.assertDictEqual(spec.inspect(), {})

        conductor = conducting.WorkflowConductor(spec)
        conductor.request_workflow_status(statuses.RUNNING)

        # Mock the action execution for each item and assert expected task statuses.
        task_route = 0
        task_name = 'task1'
        task_ctx = {'xs': ['fee', 'fi', 'fo', 'fum']}

        task_action_specs = [
            {'action': 'core.echo', 'input': {'message': 'fee'}, 'item_id': 0},
            {'action': 'core.echo', 'input': {'message': 'fi'}, 'item_id': 1},
            {'action': 'core.echo', 'input': {'message': 'fo'}, 'item_id': 2},
            {'action': 'core.echo', 'input': {'message': 'fum'}, 'item_id': 3},
        ]

        # Verify the set of action executions.
        expected_task = self.format_task_item(
            task_name,
            task_route,
            task_ctx,
            conductor.spec.tasks.get_task(task_name),
            actions=task_action_specs,
            items_count=len(task_ctx['xs'])
        )

        expected_tasks = [expected_task]
        actual_tasks = conductor.get_next_tasks()
        self.assert_task_list(conductor, actual_tasks, expected_tasks)

        # Set the items to running status.
        for i in range(0, len(task_ctx['xs'])):
            context = {'item_id': i}
            self.forward_task_statuses(conductor, task_name, [statuses.RUNNING], [context])

        # Assert that the task is running.
        actual_task_status = conductor.workflow_state.get_task(task_name, task_route)['status']
        self.assertEqual(actual_task_status, statuses.RUNNING)

        # Cancel the workflow.
        conductor.request_workflow_status(statuses.CANCELED)
        self.assertEqual(conductor.get_workflow_status(), statuses.CANCELING)
        actual_task_status = conductor.workflow_state.get_task(task_name, task_route)['status']
        self.assertEqual(actual_task_status, statuses.CANCELING)

        # Complete the items.
        for i in range(0, len(task_ctx['xs'])):
            contexts = [{'item_id': i}]
            results = [task_ctx['xs'][i]]
            status_changes = [statuses.SUCCEEDED]
            self.forward_task_statuses(conductor, task_name, status_changes, contexts, results)

        # Assert the task is completed and workflow is canceled.
        actual_task_status = conductor.workflow_state.get_task(task_name, task_route)['status']
        self.assertEqual(actual_task_status, statuses.SUCCEEDED)
        self.assertEqual(conductor.get_workflow_status(), statuses.CANCELED)

    def test_cancel_workflow_using_canceling_status_with_items_concurrency(self):
        wf_def = """
        version: 1.0

        vars:
          - xs:
              - fee
              - fi
              - fo
              - fum

        tasks:
          task1:
            with:
              items: <% ctx(xs) %>
              concurrency: 2
            action: core.echo message=<% item() %>
            next:
              - publish:
                  - items: <% result() %>

        output:
          - items: <% ctx(items) %>
        """

        concurrency = 2

        spec = native_specs.WorkflowSpec(wf_def)
        self.assertDictEqual(spec.inspect(), {})

        conductor = conducting.WorkflowConductor(spec)
        conductor.request_workflow_status(statuses.RUNNING)

        # Mock the action execution for each item and assert expected task statuses.
        task_route = 0
        task_name = 'task1'
        task_ctx = {'xs': ['fee', 'fi', 'fo', 'fum']}

        task_action_specs = [
            {'action': 'core.echo', 'input': {'message': 'fee'}, 'item_id': 0},
            {'action': 'core.echo', 'input': {'message': 'fi'}, 'item_id': 1},
            {'action': 'core.echo', 'input': {'message': 'fo'}, 'item_id': 2},
            {'action': 'core.echo', 'input': {'message': 'fum'}, 'item_id': 3},
        ]

        mock_ac_ex_statuses = [statuses.SUCCEEDED] * 2
        expected_task_statuses = [statuses.RUNNING] * 2
        expected_workflow_statuses = [statuses.RUNNING] * 2

        self.assert_task_items(
            conductor,
            task_name,
            task_route,
            task_ctx,
            task_ctx['xs'],
            task_action_specs,
            mock_ac_ex_statuses,
            expected_task_statuses,
            expected_workflow_statuses,
            concurrency=concurrency
        )

        # Assert the task is not removed from staging.
        self.assertIsNotNone(conductor.workflow_state.get_staged_task(task_name, task_route))

        # Assert the workflow is still running.
        self.assertEqual(conductor.get_workflow_status(), statuses.RUNNING)

        # Cancel the workflow.
        conductor.request_workflow_status(statuses.CANCELING)
        self.assertEqual(conductor.get_workflow_status(), statuses.CANCELED)
        actual_task_status = conductor.workflow_state.get_task(task_name, task_route)['status']
        self.assertEqual(actual_task_status, statuses.CANCELED)

    def test_cancel_workflow_using_canceled_status_with_items_concurrency(self):
        wf_def = """
        version: 1.0

        vars:
          - xs:
              - fee
              - fi
              - fo
              - fum

        tasks:
          task1:
            with:
              items: <% ctx(xs) %>
              concurrency: 2
            action: core.echo message=<% item() %>
            next:
              - publish:
                  - items: <% result() %>

        output:
          - items: <% ctx(items) %>
        """

        concurrency = 2

        spec = native_specs.WorkflowSpec(wf_def)
        self.assertDictEqual(spec.inspect(), {})

        conductor = conducting.WorkflowConductor(spec)
        conductor.request_workflow_status(statuses.RUNNING)

        # Mock the action execution for each item and assert expected task statuses.
        task_route = 0
        task_name = 'task1'
        task_ctx = {'xs': ['fee', 'fi', 'fo', 'fum']}

        task_action_specs = [
            {'action': 'core.echo', 'input': {'message': 'fee'}, 'item_id': 0},
            {'action': 'core.echo', 'input': {'message': 'fi'}, 'item_id': 1},
            {'action': 'core.echo', 'input': {'message': 'fo'}, 'item_id': 2},
            {'action': 'core.echo', 'input': {'message': 'fum'}, 'item_id': 3},
        ]

        mock_ac_ex_statuses = [statuses.SUCCEEDED] * 2
        expected_task_statuses = [statuses.RUNNING] * 2
        expected_workflow_statuses = [statuses.RUNNING] * 2

        self.assert_task_items(
            conductor,
            task_name,
            task_route,
            task_ctx,
            task_ctx['xs'],
            task_action_specs,
            mock_ac_ex_statuses,
            expected_task_statuses,
            expected_workflow_statuses,
            concurrency=concurrency
        )

        # Assert the task is not removed from staging.
        self.assertIsNotNone(conductor.workflow_state.get_staged_task(task_name, task_route))

        # Assert the workflow is still running.
        self.assertEqual(conductor.get_workflow_status(), statuses.RUNNING)

        # Cancel the workflow.
        conductor.request_workflow_status(statuses.CANCELED)
        self.assertEqual(conductor.get_workflow_status(), statuses.CANCELED)
        actual_task_status = conductor.workflow_state.get_task(task_name, task_route)['status']
        self.assertEqual(actual_task_status, statuses.CANCELED)

    def test_cancel_workflow_with_items_concurrency_and_active(self):
        wf_def = """
        version: 1.0

        vars:
          - xs:
              - fee
              - fi
              - fo
              - fum

        tasks:
          task1:
            with:
              items: <% ctx(xs) %>
              concurrency: 2
            action: core.echo message=<% item() %>
            next:
              - publish:
                  - items: <% result() %>

        output:
          - items: <% ctx(items) %>
        """

        concurrency = 2

        spec = native_specs.WorkflowSpec(wf_def)
        self.assertDictEqual(spec.inspect(), {})

        conductor = conducting.WorkflowConductor(spec)
        conductor.request_workflow_status(statuses.RUNNING)

        # Mock the action execution for each item and assert expected task statuses.
        task_route = 0
        task_name = 'task1'
        task_ctx = {'xs': ['fee', 'fi', 'fo', 'fum']}

        task_action_specs = [
            {'action': 'core.echo', 'input': {'message': 'fee'}, 'item_id': 0},
            {'action': 'core.echo', 'input': {'message': 'fi'}, 'item_id': 1},
            {'action': 'core.echo', 'input': {'message': 'fo'}, 'item_id': 2},
            {'action': 'core.echo', 'input': {'message': 'fum'}, 'item_id': 3},
        ]

        # Verify the first set of action executions.
        expected_task = self.format_task_item(
            task_name,
            task_route,
            task_ctx,
            conductor.spec.tasks.get_task(task_name),
            actions=task_action_specs[0:concurrency],
            items_count=len(task_ctx['xs']),
            items_concurrency=concurrency
        )

        expected_tasks = [expected_task]
        actual_tasks = conductor.get_next_tasks()
        self.assert_task_list(conductor, actual_tasks, expected_tasks)

        # Set the items to running status.
        for i in range(0, concurrency):
            context = {'item_id': i}
            self.forward_task_statuses(conductor, task_name, [statuses.RUNNING], [context])

        # Assert that the task is running.
        actual_task_status = conductor.workflow_state.get_task(task_name, task_route)['status']
        self.assertEqual(actual_task_status, statuses.RUNNING)

        # Cancel the workflow.
        conductor.request_workflow_status(statuses.CANCELING)
        self.assertEqual(conductor.get_workflow_status(), statuses.CANCELING)
        actual_task_status = conductor.workflow_state.get_task(task_name, task_route)['status']
        self.assertEqual(actual_task_status, statuses.CANCELING)

        # Complete the items.
        for i in range(0, concurrency):
            contexts = [{'item_id': i}]
            results = [task_ctx['xs'][i]]
            status_changes = [statuses.SUCCEEDED]
            self.forward_task_statuses(conductor, task_name, status_changes, contexts, results)

        # Assert the task and workflow are canceled.
        actual_task_status = conductor.workflow_state.get_task(task_name, task_route)['status']
        self.assertEqual(actual_task_status, statuses.CANCELED)
        self.assertEqual(conductor.get_workflow_status(), statuses.CANCELED)
