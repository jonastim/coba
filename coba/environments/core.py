import json
import collections.abc

from urllib import request
from pathlib import Path
from zipfile import ZipFile, BadZipFile
from typing import Sequence, overload, Union, Iterable, Iterator, Any, Optional, Tuple, Callable, Mapping, Type, Literal

from coba                 import pipes
from coba.context         import CobaContext, DiskCacher, DecoratedLogger, ExceptLog, NameLog, StampLog
from coba.primitives      import Context, Action, Source, Learner, Environment, EnvironmentFilter
from coba.random          import CobaRandom
from coba.pipes           import Pipes, HttpSource, IterableSource, DataFrameSource, DiskSource, NextSource
from coba.exceptions      import CobaException
from coba.multiprocessing import CobaMultiprocessor

from coba.environments.templates  import EnvironmentsTemplateV1, EnvironmentsTemplateV2
from coba.environments.openml     import OpenmlSimulation
from coba.environments.synthetics import LinearSyntheticSimulation, NeighborsSyntheticSimulation
from coba.environments.synthetics import KernelSyntheticSimulation, MLPSyntheticSimulation, LambdaSimulation
from coba.environments.supervised import SupervisedSimulation
from coba.environments.results    import ResultEnvironment

from coba.environments.filters   import Repr, Batch, Chunk, Logged, Materialize
from coba.environments.filters   import Binary, Shuffle, Take, Sparsify, Densify, Reservoir, Cycle, Scale, Unbatch
from coba.environments.filters   import Slice, Impute, Where, Riffle, Sort, Flatten, Cache, Params, Grounded
from coba.environments.filters   import MappingToInteraction, OpeRewards, Noise

from coba.environments.serialized import EnvironmentFromObjects, EnvironmentsToObjects, ZipMemberToObjects, ObjectsToZipMember

class Environments(collections.abc.Sequence, Sequence[Environment]):
    """A friendly wrapper around commonly used environment functionality."""

    @staticmethod
    def cache_dir(path:Union[str,Path]) -> Type['Environments']:
        CobaContext.cacher = DiskCacher(path)
        return Environments

    @overload
    @staticmethod
    def from_template(filesource:Source[Iterable[str]], **user_vars) -> 'Environments': ...

    @overload
    @staticmethod
    def from_template(fileurl:str, **user_vars) -> 'Environments': ...

    @staticmethod
    def from_template(arg, **user_vars) -> 'Environments':
        """Instantiate Environments from an environment template file with user defined variables."""
        try:
            return Environments(*EnvironmentsTemplateV2(arg, **user_vars).read())
        except Exception as e: #pragma: no cover
            try:
                #try previous version of definition files. If previous versions also fail
                #then we raise the exception given by the most up-to-date version so that
                #changes can be made to conform to the latest version.
                return Environments(*EnvironmentsTemplateV1(arg).read())
            except:
                raise e

    @staticmethod
    def from_prebuilt(name:str) -> 'Environments':
        """Instantiate Environments from a pre-built definition made for diagnostics and comparisons across projects."""

        repo_url       = "https://github.com/mrucker/coba_prebuilds/blob/main"
        definition_url = f"{repo_url}/{name}/index.json?raw=True"

        try:
            definition_txt = HttpSource(definition_url).read()
        except request.HTTPError as e:
            if e.code != 404:
                raise
            else:
                root_dir_text = HttpSource("https://api.github.com/repos/mrucker/coba_prebuilds/contents/").read()
                root_dir_json = json.loads(root_dir_text)
                known_names   = [ obj['name'] for obj in root_dir_json if obj['name'] != "README.md" ]
                raise CobaException(f"The given prebuilt name, {name}, couldn't be found. Known names are: {known_names}")

        definition_txt = definition_txt.replace('"./', f'"{repo_url}/{name}/')
        definition_txt = definition_txt.replace('.json"', '.json?raw=True"')
        return Environments.from_template(IterableSource([definition_txt]))

    @staticmethod
    def from_linear_synthetic(
        n_interactions: int,
        n_actions:int = 5,
        n_context_features: int = 5,
        n_action_features: int = 5,
        reward_features: Sequence[str] = ["a","xa"],
        seed: Union[int,Sequence[int]] = 1) -> 'Environments':
        """A synthetic simulation whose rewards are linear with respect to the given reward features.

        The simulation's rewards are determined via a linear function with respect to the given reward features. When
        no context or action features are requested reward features are calculted using a constant feature of 1 for
        non-existant features.
        """

        seed = [seed] if not isinstance(seed,collections.abc.Sequence) else seed
        args = (n_interactions, n_actions, n_context_features, n_action_features, reward_features)

        return Environments([LinearSyntheticSimulation(*args, s) for s in seed])

    @staticmethod
    def from_neighbors_synthetic(
        n_interactions: int,
        n_actions: int = 2,
        n_context_features: int = 5,
        n_action_features: int = 5,
        n_neighborhoods: int = 30,
        seed: int = 1) -> 'Environments':
        """A synthetic simulation whose reward values are determined by neighborhoods.

        The simulation's rewards are determined by the neighborhood (location) of given
        context and action pairs. A neighborhood's reward is determined by random assignment.
        """

        seed = [seed] if not isinstance(seed,collections.abc.Sequence) else seed
        args = (n_interactions, n_actions, n_context_features, n_action_features, n_neighborhoods)

        return Environments([NeighborsSyntheticSimulation(*args, s) for s in seed])

    @staticmethod
    def from_kernel_synthetic(
        n_interactions:int,
        n_actions:int = 10,
        n_context_features:int = 10,
        n_action_features:int = 10,
        n_exemplars:int = 10,
        kernel: Literal['linear','polynomial','exponential','gaussian'] = 'gaussian',
        degree: int = 3,
        gamma: float = 1,
        seed: Union[int,Sequence[int]] = 1) -> 'Environments':
        """A synthetic simulation whose reward function is created from kernel basis functions."""

        seed = [seed] if not isinstance(seed,collections.abc.Sequence) else seed
        args = (n_interactions, n_actions, n_context_features, n_action_features, n_exemplars, kernel, degree, gamma)

        return Environments([KernelSyntheticSimulation(*args, s) for s in seed])

    @staticmethod
    def from_mlp_synthetic(
        n_interactions:int,
        n_actions:int = 10,
        n_context_features:int = 10,
        n_action_features:int = 10,
        seed: int = 1) -> 'Environments':
        """A synthetic simulation whose reward function belongs to the MLP family.

        The MLP architecture has a single hidden layer with sigmoid activation and one output
        value calculated from a random linear combination of the hidden layer's output.
        """

        seed = [seed] if not isinstance(seed,collections.abc.Sequence) else seed
        args = (n_interactions, n_actions, n_context_features, n_action_features)

        return Environments([MLPSyntheticSimulation(*args, s) for s in seed])

    @overload
    @staticmethod
    def from_openml(data_id: Union[int,Sequence[int]],
        drop_missing: bool = True,
        take: int = None,
        *,
        target:str = None,
        label_type:Literal['c','r','m'] = None) -> 'Environments':
        ...

    @overload
    @staticmethod
    def from_openml(*,task_id: Union[int,Sequence[int]],
        drop_missing: bool = True,
        take: int = None,
        target:str = None,
        label_type:Literal['m','c','r'] = None) -> 'Environments':
        ...

    @staticmethod
    def from_openml(*args,**kwargs) -> 'Environments':
        """Create a SimulatedEnvironment from datasets available on openml."""

        kwargs.update(zip(['data_id','drop_missing','take'], args))

        if 'data_id' in kwargs and isinstance(kwargs['data_id'],int):
            kwargs['data_id'] = [kwargs['data_id']]

        if 'task_id' in kwargs and isinstance(kwargs['task_id'],int):
            kwargs['task_id'] = [kwargs['task_id']]

        if 'data_id' in kwargs:
            return Environments(*[OpenmlSimulation(data_id=id, **kwargs) for id in kwargs.pop('data_id')])
        else:
            return Environments(*[OpenmlSimulation(task_id=id, **kwargs) for id in kwargs.pop('task_id')])

    @overload
    @staticmethod
    def from_supervised(
        source: Source,
        label_col: Union[int,str] = None,
        label_type: Literal["C","R"] = "C",
        take: int = None) -> 'Environments':
        """Create a SimulatedEnvironment from a supervised dataset"""
        ...

    @overload
    @staticmethod
    def from_supervised(
        X = Sequence[Any],
        Y = Sequence[Any],
        label_type: Literal["C","R"] = "C") -> 'Environments':
        """Create a SimulatedEnvironment from a supervised dataset"""
        ...

    @staticmethod
    def from_supervised(*args, **kwargs) -> 'Environments':
        """Create a SimulatedEnvironment from a supervised dataset"""
        return Environments(SupervisedSimulation(*args, **kwargs))

    @staticmethod
    def from_save(path:str) -> 'Environments':
        envs = []
        for name in ZipFile(path).namelist():
            envs.append(EnvironmentFromObjects(ZipMemberToObjects(path,name)))
        return Environments(envs)

    @overload
    def from_lambda(self,
        n_interactions: Optional[int],
        context       : Callable[[int               ],Context         ],
        actions       : Callable[[int,Context       ],Sequence[Action]],
        reward        : Callable[[int,Context,Action],float           ]) -> 'Environments':
        """Create a SimulatedEnvironment from lambda functions."""

    @overload
    def from_lambda(self,
        n_interactions: Optional[int],
        context       : Callable[[int               ,CobaRandom],Context         ],
        actions       : Callable[[int,Context       ,CobaRandom],Sequence[Action]],
        reward        : Callable[[int,Context,Action,CobaRandom],float           ],
        seed          : int) -> 'Environments':
        """Create a SimulatedEnvironment from lambda functions."""

    @staticmethod
    def from_lambda(*args,**kwargs) -> 'Environments':
        """Create a SimulatedEnvironment from lambda functions."""
        return Environments(LambdaSimulation(*args,**kwargs))

    @staticmethod
    def from_dataframe(df) -> 'Environments':
        return Environments(Pipes.join(DataFrameSource(df), MappingToInteraction()))

    @staticmethod
    def from_result(path:str) -> 'Environments':
        env_rows = collections.defaultdict(dict)
        lrn_rows = collections.defaultdict(dict)
        val_rows = collections.defaultdict(dict)
        interactions = []

        for (loc,line) in DiskSource(path,include_loc=True).read():
            if line.strip():
                trx = json.loads(line)
                if trx[0] == "E": env_rows[trx[1]].update(trx[2])
                if trx[0] == "L": lrn_rows[trx[1]].update(trx[2])
                if trx[0] == "V": val_rows[trx[1]].update(trx[2])
                if trx[0] == "I": interactions.append((loc,*trx[1],0)[:4] )

        envs = []
        for loc, env_id, lrn_id, val_id in interactions:
            env_params = env_rows.get(env_id)
            lrn_params = lrn_rows.get(lrn_id)
            val_params = val_rows.get(val_id)
            int_source = NextSource(DiskSource(path,start_loc=loc))
            envs.append(ResultEnvironment(int_source,env_params,lrn_params,val_params))

        return Environments(envs)

    @staticmethod
    def from_given(*environments: Union[Environment, Sequence[Environment]]):
        return Environments(*environments)

    @staticmethod
    def from_feurer(drop_missing: bool = True) -> 'Environments':
        """Create environments from the 247 openml tasks in https://arxiv.org/abs/2007.04074.

        Args:
            drop_missing: Exclude interactions with missing context features.

        Remarks:
            For Task ids 232, 3044, 75105, and 211723 every row has a missing feature. These
            environments will be empty when drop_missing is True. Task id 189866 has been
            updated to 361282, a new version of the original dataset that fixes api issues
            with the old dataset.

        """

        task_ids = [232,236,241,245,253,254,256,258,260,262,267,271,273,275,279,288,336,340,
                    2119,2120,2121,2122,2123,2125,2356,3044,3047,3048,3049,3053,3054,3055,
                    75089,75092,75093,75097,75098,75100,75105,75108,75109,75112,75114,75115,
                    75116,75118,75120,75121,75125,75126,75127,75129,75131,75133,75134,75136,
                    75139,75141,75142,75143,75146,75147,75148,75149,75153,75154,75156,75157,
                    75159,75161,75163,75166,75169,75171,75173,75174,75176,75178,75179,75180,
                    75184,75185,75187,75192,75193,75195,75196,75199,75210,75212,75213,75215,
                    75217,75219,75221,75223,75225,75232,75233,75234,75235,75236,75237,75239,
                    75250,126021,126024,126025,126026,126028,126029,126030,126031,146574,146575,
                    146576,146577,146578,146583,146586,146592,146593,146594,146596,146597,146600,
                    146601,146602,146603,146679,166859,166866,166872,166875,166882,166897,166905,
                    166906,166913,166915,166931,166932,166944,166950,166951,166953,166956,166957,
                    166958,166959,166970,166996,167083,167085,167086,167087,167088,167089,167090,
                    167094,167096,167097,167099,167100,167101,167103,167104,167105,167106,167149,
                    167152,167161,167168,167181,167184,167185,167190,167200,167201,167202,167203,
                    167204,167205,168785,168791,168792,168793,168794,168795,168796,168797,168798,
                    189779,189786,189828,189829,189836,189840,189841,189843,189844,189845,189846,
                    189858,189859,189860,189861,189862,189863,189864,189865,361282,189869,189870,
                    189871,189872,189873,189874,189875,189878,189880,189881,189882,189883,189884,
                    189887,189890,189893,189894,189899,189900,189902,189905,189906,189908,189909,
                    190154,190155,190156,190157,190158,190159,211720,211721,211722,211723,211724]

        return Environments.from_openml(task_id=task_ids,drop_missing=drop_missing)

    def __init__(self, *environments: Union[Environment, Sequence[Environment]]):
        """Instantiate an Environments class.

        Args:
            *environments: The base environments to initialize the class.
        """
        self._environments = []

        for env in environments:
            if isinstance(env, (collections.abc.Sequence,collections.abc.Generator)):
                self._environments.extend(env)
            else:
                self._environments.append(env)

    def binary(self) -> 'Environments':
        """Binarize all rewards to either 1 (max rewards) or 0 (all others)."""
        return self.filter(Binary())

    def sparse(self, context:bool = True, action:bool = False) -> 'Environments':
        """Convert all environments to a sparse representation."""
        return self.filter(Sparsify(context,action))

    def dense(self, n_feats:int, method:Literal['lookup','hashing'], context:bool = True, action:bool = False) -> 'Environments':
        """Convert all environments to a dense representation."""
        make_dense = lambda: Densify(n_feats=n_feats, method=method, context=context, action=action)
        return Environments([Pipes.join(env, make_dense()) for env in self])

    @overload
    def shuffle(self, seed: int = 1) -> 'Environments':
        ...

    @overload
    def shuffle(self, seeds: Iterable[int]) -> 'Environments':
        ...

    @overload
    def shuffle(self, *, n:int) -> 'Environments':
        ...

    def shuffle(self, *args,**kwargs) -> 'Environments':
        """Shuffle the order of the interactions in the Environments."""

        flat = lambda a: next(pipes.Flatten().filter([a]))

        if kwargs and 'n' in kwargs:
            seeds = range(kwargs['n'])
        else:
            args = kwargs.get('seed',kwargs.get('seeds',args))
            seeds = flat(args) or [1]

        if isinstance(seeds,int): seeds = [seeds]

        shuffled = self.filter([Shuffle(seed) for seed in seeds])

        #Experience has shown that most of the time we want to sort.
        #This doesn't change the experiment results. It simply makes it
        #easier monitor an experiment while it runs in the background.
        ordered = sorted(shuffled, key=lambda env: env.params.get('shuffle',0))

        return Environments(ordered)

    def sort(self, *keys: Union[str,int,Sequence[Union[str,int]]]) -> 'Environments':
        """Sort Environment interactions according to the context values indicated by keys."""
        return self.filter(Sort(*keys))

    def riffle(self, spacing: int, seed: int = 1) -> 'Environments':
        """Riffle shuffle by evenly spacing interactions at the end of an environment into the beginning."""
        return self.filter(Riffle(spacing, seed))

    def cycle(self, after: int) -> 'Environments':
        """Cycle all rewards associated with actions by one place."""
        if isinstance(after,(int,float)): after = [after]
        return self.filter([Cycle(a) for a in after])

    def params(self, params: Mapping[str,Any]) -> 'Environments':
        """Add params to the environments."""
        return self.filter(Params(params))

    def take(self, n_interactions: int, strict: bool = False) -> 'Environments':
        """Take a fixed number of interactions from the Environments."""
        return self.filter(Take(n_interactions, strict))

    def slice(self, start: Optional[int], stop: Optional[int]=None, step:int = 1) -> 'Environments':
        """Take a slice of interactions from an Environment."""
        return self.filter(Slice(start,stop,step))

    def reservoir(self, n_interactions: int, seeds: Union[int,Sequence[int]]=1, strict:bool = False) -> 'Environments':
        """Take a random fixed number of interactions from the Environments."""
        if isinstance(seeds,int): seeds = [seeds]
        return self.filter([Reservoir(n_interactions,strict=strict,seed=seed) for seed in seeds])

    def scale(self,
        shift: Union[float,Literal["min","mean","med"]] = "min",
        scale: Union[float,Literal["minmax","std","iqr","maxabs"]] = "minmax",
        targets:Literal["context"] = "context",
        using: Optional[int] = None) -> 'Environments':
        """Apply an affine shift and scaling factor to precondition environment features."""
        if isinstance(targets,str): targets = [targets]
        return self.filter(Pipes.join(*[Scale(shift, scale, t, using) for t in targets]))

    def impute(self,
        stats: Union[Literal["mean","median","mode"],Sequence[Literal["mean","median","mode"]]] = "mean",
        indicator:bool = True,
        using: Optional[int] = None) -> 'Environments':
        """Impute missing values with a feature statistic using a given number of interactions."""
        if isinstance(stats,str): stats = [stats]
        envs = self
        for stat in stats:
            envs = self.filter(Impute(stat, indicator, using))
        return envs

    def where(self,*,n_interactions: Union[int,Tuple[Optional[int],Optional[int]]] = None) -> 'Environments':
        """Only include environments which satisify the given requirements."""
        return self.filter(Where(n_interactions=n_interactions))

    def noise(self,
        context: Union[Tuple[float,float],Callable[[float,CobaRandom], float]] = None,
        action : Union[Tuple[float,float],Callable[[float,CobaRandom], float]] = None,
        reward : Union[Tuple[float,float],Callable[[float,CobaRandom], float]] = None,
        seed   : Union[int,Sequence[int]] = 1) -> 'Environments':
        """Add noise to an environment's context, actions and rewards."""
        if isinstance(seed,(int,float)): seed = [seed]
        return self.filter([Noise(context,action,reward,s) for s in seed])

    def flat(self) -> 'Environments':
        """Flatten environment's context and actions."""
        return self.filter(Flatten())

    def materialize(self) -> 'Environments':
        """Materialize the environments in memory. Ideal for stateful environments such as Jupyter Notebook."""
        #we use pipes.cache directly because the environment cache will copy
        #which we don't need when we materialize an environment in memory
        envs = Environments([Pipes.join(env, Materialize(), pipes.Cache(25,True)) for env in self])

        for env in envs: list(env.read()) #force read to pre-load cache

        for env in envs:
            for i in range(len(env)-1):
                pipe = env[i]
                if isinstance(pipe, pipes.Cache) and not pipe._protected:
                    pipe._cache = None

        return envs

    def grounded(self, n_users: int, n_normal:int, n_words:int, n_good:int, seed:int=1) -> 'Environments':
        """Convert from simulated environments to interaction grounded environments."""
        return self.filter(Grounded(n_users, n_normal, n_words, n_good, seed))

    def repr(self,
        cat_context:Literal["onehot","onehot_tuple","string"] = "onehot",
        cat_actions:Literal["onehot","onehot_tuple","string"] = "onehot") -> 'Environments':
        """Determine how certain types of data is represented."""
        return self.filter(Repr(cat_context,cat_actions))

    def batch(self, batch_size:int) -> 'Environments':
        """Batch interactions for learning and evaluation."""
        return self.filter(Batch(batch_size))

    def chunk(self, cache:bool = True) -> 'Environments':
        """Create a chunk point in the environments pipeline to compose how multiprocess is conducted."""
        envs = Environments([Pipes.join(env, Chunk()) for env in self])
        return envs.cache() if cache else envs

    def logged(self, learners: Union[Learner,Sequence[Learner]], seed:Optional[float] = 1.23) -> 'Environments':
        """Create a logged environment using the given learner for the logging policy."""
        if not isinstance(learners, collections.abc.Sequence): learners = [learners]
        return self.filter([Logged(learner, seed) for learner in learners ])

    def unbatch(self):
        """Unbatch interactions in the environments."""
        return self.filter(Unbatch())

    def ope_rewards(self, rewards_type:Literal['IPS','DM','DR'] = None):
        """Reward estimates for off-policy evaluation."""
        if isinstance(rewards_type,str): rewards_type = [rewards_type]
        return self.filter([OpeRewards(r) for r in rewards_type])

    def save(self, path: str, processes:int=1, overwrite:bool=False) -> 'Environments':
        """Save the environments to disk."""
        self_envs = list(self)
        if Path(path).exists():
            try:
                path_envs   = Environments.from_save(path)
                path_params = [e.params for e in path_envs]
                self_params = [e.params for e in self_envs]

                try:
                    while path_params:
                        param_index_in_self = self_params.index(path_params.pop())
                        self_params.pop(param_index_in_self)
                        self_envs.pop(param_index_in_self)
                except ValueError:
                    #there is a param in the file that isn't in self
                    is_equal = False
                else:
                    is_equal = True

                if is_equal and not self_envs:
                    return path_envs
                if not is_equal and overwrite:
                    Path(path).unlink()
                if not is_equal and not overwrite:
                    raise CobaException("The Environments save file does not match the actual Environments and overwite is False.")

            except BadZipFile:
                if overwrite:
                    Path(path).unlink()
                else:
                    raise CobaException("The given save file appears to be corrupted. Please check it and delete if it is unusable.")

        CobaContext.logger = DecoratedLogger([ExceptLog()], CobaContext.logger, [StampLog()] if processes ==1 else [NameLog(), StampLog()])
        Pipes.join(IterableSource(self_envs),CobaMultiprocessor(EnvironmentsToObjects(),processes),ObjectsToZipMember(path)).run()
        CobaContext.logger = CobaContext.logger.undecorate()

        return Environments.from_save(path)

    def cache(self) -> 'Environments':
        """Create a cache point in the environments so that earlier steps in the pipeline can be re-used in several pipes."""
        return Environments([Pipes.join(env, Cache(25)) for env in self])

    def filter(self, filter: Union[EnvironmentFilter,Sequence[EnvironmentFilter]]) -> 'Environments':
        """Apply filters to each environment currently in Environments."""
        filters = filter if isinstance(filter, collections.abc.Sequence) else [filter]
        return Environments([Pipes.join(e,f) for e in self._environments for f in filters])

    def __getitem__(self, index:Any) -> Union[Environment,'Environments']:
        if isinstance(index,slice):
            return Environments(self._environments[index])
        else:
            return self._environments[index]

    def __iter__(self) -> Iterator[Environment]:
        return iter(self._environments)

    def __len__(self) -> int:
        return len(self._environments)

    def __add__(self, other: 'Environments') -> 'Environments':
        return Environments(self._environments+other._environments)

    def __str__(self) -> str:
        return "\n".join([f"{i+1}. {e}" for i,e in enumerate(self._environments)])

    def _ipython_display_(self):
        #pretty print in jupyter notebook (https://ipython.readthedocs.io/en/stable/config/integrating.html)
        print(str(self))
