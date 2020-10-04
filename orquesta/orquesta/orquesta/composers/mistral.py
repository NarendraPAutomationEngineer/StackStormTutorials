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

import logging
from six.moves import queue

from orquesta.composers import base as comp_base
from orquesta import graphing
from orquesta.specs import mistral as mistral_specs
from orquesta import statuses


LOG = logging.getLogger(__name__)

TASK_TRANSITION_MAP = {
    'on-success': [statuses.SUCCEEDED],
    'on-error': statuses.ABENDED_STATUSES,
    'on-complete': statuses.COMPLETED_STATUSES
}


class WorkflowComposer(comp_base.WorkflowComposer):
    wf_spec_type = mistral_specs.WorkflowSpec

    @classmethod
    def compose(cls, spec):
        if not cls.wf_spec_type:
            raise TypeError('Undefined spec type for composer.')

        if not isinstance(spec, cls.wf_spec_type):
            raise TypeError('Unsupported spec type "%s".' % str(type(spec)))

        return cls._compose_wf_graph(spec)

    @classmethod
    def _compose_transition_criteria(cls, task_name, *args, **kwargs):
        criteria = []

        condition = kwargs.get('condition')
        expr = kwargs.get('expr')

        task_status_criterion = (
            'task_status(%s) in %s' % (task_name, str(TASK_TRANSITION_MAP[condition]))
        )

        criteria.append('<% ' + task_status_criterion + ' %>')

        if expr:
            criteria.append(expr)

        return criteria

    @classmethod
    def _compose_wf_graph(cls, wf_spec):
        if not isinstance(wf_spec, cls.wf_spec_type):
            raise TypeError('Workflow spec is not typeof %s.' % cls.wf_spec_type.__name__)

        q = queue.Queue()
        wf_graph = graphing.WorkflowGraph()

        for task_name, expr, condition in wf_spec.tasks.get_start_tasks():
            q.put((task_name, []))

        while not q.empty():
            task_name, splits = q.get()

            wf_graph.add_task(task_name)

            if wf_spec.tasks.is_join_task(task_name):
                task_spec = wf_spec.tasks[task_name]
                barrier = '*' if task_spec.join == 'all' else task_spec.join
                wf_graph.set_barrier(task_name, value=barrier)

            # Determine if the task is a split task and if it is in a cycle. If the task is a
            # split task, keep track of where the split(s) occurs.
            if wf_spec.tasks.is_split_task(task_name) and not wf_spec.tasks.in_cycle(task_name):
                splits.append(task_name)

            if splits:
                wf_graph.update_task(task_name, splits=splits)

            next_tasks = wf_spec.tasks.get_next_tasks(task_name)

            for next_task_name, expr, condition in next_tasks:
                if (not wf_graph.has_task(next_task_name) or
                        not wf_spec.tasks.in_cycle(next_task_name)):
                    q.put((next_task_name, list(splits)))

                crta = cls._compose_transition_criteria(task_name, condition=condition, expr=expr)
                seqs = wf_graph.has_transition(task_name, next_task_name, criteria=crta)

                # Use existing transition if present otherwise create new transition.
                if seqs:
                    wf_graph.update_transition(
                        task_name,
                        next_task_name,
                        key=seqs[0][2],
                        criteria=crta
                    )
                else:
                    wf_graph.add_transition(
                        task_name,
                        next_task_name,
                        criteria=crta
                    )

        return wf_graph
