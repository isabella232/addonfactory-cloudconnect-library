import copy
import threading

from cloudconnectlib.common.log import CloudClientLogAdapter
from cloudconnectlib.splunktacollectorlib.common import log
from task import BaseTask


class CCEJob(object):
    """
    One CCEJob is composed of a list of tasks. The task could be HTTP
     task or Split task(currently supported task types).
    Job is an executing unit of CCE engine.
    All tasks in one job will be run sequentially but different jobs
    could be run concurrently.
    So if there is no dependency among tasks, then suggest to create
    different Job for them to improve performance.
    """

    def __init__(self, context, name=None, tasks=None):
        self._context = context
        self._rest_tasks = []

        self._stop_signal_received = False
        self._stopped = threading.Event()

        if tasks:
            self._rest_tasks.extend(tasks)
        self._logger = CloudClientLogAdapter(log.logger, prefix=name)
        self._running_task = None

    def add_task(self, task):
        """
        Add a task instance into a job.

        :param task: TBD
        :type task: TBD
        """
        if not isinstance(task, BaseTask):
            raise ValueError('Unsupported task type: {}'.format(type(task)))
        self._rest_tasks.append(task)

    def _check_if_stop_needed(self):
        if self._stop_signal_received:
            self._logger.info('Stop job signal received, stopping job.')
            self._stopped.set()
            return True
        return False

    def run(self):
        """
        Run current job, which executes tasks in it sequentially..

        :param context:
        :type context: dict
        """
        self._logger.debug('Start to run job')

        if not self._rest_tasks:
            self._logger.info('No task found in job')
            return

        if self._check_if_stop_needed():
            return

        self._running_task = self._rest_tasks[0]
        self._rest_tasks = self._rest_tasks[1:]
        contexts = list(self._running_task.perform(self._context) or ())

        if self._check_if_stop_needed():
            return

        if not self._rest_tasks:
            self._logger.info('No more task need to perform, exiting job')
            return

        count = 0

        for ctx in contexts:
            count += 1
            yield CCEJob(context=copy.deepcopy(ctx),
                         tasks=copy.deepcopy(self._rest_tasks))

            if self._check_if_stop_needed():
                break

        self._logger.debug('Generated %s job in total', count)
        self._logger.debug('Job execution finished successfully.')
        self._stopped.set()

    def stop(self, block=False, timeout=30):
        """
        Stop current job.
        """
        if self._stopped.is_set():
            self._logger.info('Job is not running, cannot stop it.')
            return
        self._stop_signal_received = True

        if self._running_task:
            self._running_task.stop(block, timeout)
        if not block:
            return

        if not self._stopped.wait(timeout):
            self._logger.info('Waiting for stop job timeout')
