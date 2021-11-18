from pathlib import Path
from typing_extensions import Literal
from typing import Sequence, Optional

from coba.learners import Learner
from coba.environments import Environment
from coba.config import CobaConfig
from coba.exceptions import CobaFatal
from coba.pipes import Pipe, MemoryIO
from coba.multiprocessing import CobaMultiprocessFilter

from coba.experiments.process      import CreateWorkItems,  RemoveFinished, ChunkByTask, ChunkBySource, ProcessWorkItems
from coba.experiments.tasks        import EnvironmentTask, EvaluationTask, LearnerTask
from coba.experiments.tasks        import SimpleLearnerTask, SimpleEnvironmentTask, OnPolicyEvaluationTask
from coba.experiments.results      import Result, Transaction, TransactionIO

class Experiment:
    """An Experiment which uses environments and learners to calculate performance statistics."""

    def __init__(self,
        environments    : Sequence[Environment],
        learners        : Sequence[Learner],
        learner_task    : LearnerTask     = SimpleLearnerTask(), 
        environment_task: EnvironmentTask = SimpleEnvironmentTask(),
        evaluation_task : EvaluationTask  = OnPolicyEvaluationTask()) -> None:
        """Instantiate an Experiment.

        Args:
            environments: The collection of environments to use in the experiment.
            learners: The collection of learners to use in the experiment.
            learner_task: A task which describes a learner.
            environment_task: A task which describes an environment and its interactions.
            evaluation_task: A task which evaluates performance of a learner on an environment's interactions.
        """

        self._environments      = environments
        self._learners         = learners
        self._learner_task     = learner_task
        self._environment_task = environment_task
        self._evaluation_task  = evaluation_task

        self._processes       : Optional[int] = None
        self._maxtasksperchild: Optional[int] = None
        self._chunk_by        : Optional[str] = None

    def config(self, 
        processes: int = None,
        chunk_by: Literal['source','task'] = None,
        maxtasksperchild: Optional[int] = None) -> 'Experiment':
        """Configure how the experiment will be executed. A value of `None` for any item means the global config will be used.
        
        Args:
            chunk_by: Determines how tasks are chunked for processing.
            processes: Determines how many processes to use when processing task chunks.
            maxtasksperchild: Determines how many tasks each process will complete before being restarted. A value of 0 means infinite.
        """

        assert chunk_by is None or chunk_by in ['task', 'source'], "The given chunk_by value wasn't recognized. Allowed values are 'task', 'source' and 'none'"
        assert processes is None or processes > 0, "The given number of processes is invalid. Must be greater than 0."
        assert maxtasksperchild is None or maxtasksperchild >= 0, "The given number of taks per child is invalid. Must be greater than or equal to 0 (0 for infinite)."

        self._chunk_by         = chunk_by
        self._processes        = processes
        self._maxtasksperchild = maxtasksperchild

        return self

    def evaluate(self, result_file:str = None) -> Result:
        """Evaluate the experiment and return the results.

        Args:
            result_file: The file we'd like to use for writing/restoring results experiments.
        """

        restored = Result.from_file(result_file, True) if result_file and Path(result_file).exists() else Result()

        n_given_learners     = len(self._learners)
        n_given_environments = len(self._environments)
 
        if len(restored.experiment) != 0:
            assert n_given_learners     == restored.experiment['n_learners'    ], "The current experiment doesn't match the given transaction log."
            assert n_given_environments == restored.experiment['n_environments'], "The current experiment doesn't match the given transaction log."

        preamble = []
        preamble.append(Transaction.version())
        preamble.append(Transaction.experiment(n_given_learners, n_given_environments))

        cb = self._chunk_by         if self._chunk_by         is not None else CobaConfig.experiment.chunk_by
        mp = self._processes        if self._processes        is not None else CobaConfig.experiment.processes
        mt = self._maxtasksperchild if self._maxtasksperchild is not None else CobaConfig.experiment.maxtasksperchild

        workitems  = CreateWorkItems(self._environments, self._learners, self._learner_task, self._environment_task, self._evaluation_task)
        unfinished = RemoveFinished(restored)
        chunk      = ChunkByTask() if cb == 'task' else ChunkBySource()
        sink       = TransactionIO(result_file, restored=restored, minify=True)

        single_process = ProcessWorkItems()
        multi_process  = Pipe.join([chunk, CobaMultiprocessFilter([ProcessWorkItems()], mp, mt)])
        process        = multi_process if mp > 1 or mt != 0 else single_process

        try:
            Pipe.join(MemoryIO(preamble), [], sink).run()
            Pipe.join(workitems, [unfinished, process], sink).run()
        
        except KeyboardInterrupt:
            CobaConfig.logger.log("Experiment execution was manually aborted via Ctrl-C")
        except CobaFatal:
            raise
        except Exception as ex:
            CobaConfig.logger.log_exception(ex)

        return sink.result