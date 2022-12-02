import collections.abc

from pathlib import Path
from typing import Sequence, overload, Union, Iterable, Iterator, Any, Optional, Tuple, Callable, Mapping, Type
from coba.backports import Literal

from coba            import pipes
from coba.contexts   import CobaContext, DiskCacher
from coba.random     import CobaRandom
from coba.pipes      import Pipes, Source, HttpSource, IterableSource, JsonDecode
from coba.exceptions import CobaException

from coba.environments.filters   import EnvironmentFilter, Repr, Batch, Chunk
from coba.environments.filters   import Binary, Shuffle, Take, Sparse, Reservoir, Cycle, Scale
from coba.environments.filters   import Impute, Where, Noise, Riffle, Sort, Flatten, Cache, Params, Grounded
from coba.environments.templates import EnvironmentsTemplateV1, EnvironmentsTemplateV2

from coba.environments.primitives import Environment, Context, Action

from coba.environments.simulated.synthetics import LinearSyntheticSimulation, NeighborsSyntheticSimulation
from coba.environments.simulated.synthetics import KernelSyntheticSimulation, MLPSyntheticSimulation, LambdaSimulation
from coba.environments.simulated.openml     import OpenmlSimulation
from coba.environments.simulated.supervised import SupervisedSimulation

class Environments (collections.abc.Sequence):
    """A friendly wrapper around commonly used environment functionality."""

    @staticmethod
    def cache_dir(path:Union[str,Path]) -> Type['Environments']:
        CobaContext.cacher = DiskCacher(path)
        return Environments

    @overload
    @staticmethod
    def from_template(filesource:Source[Iterable[str]]) -> 'Environments': ...

    @overload
    @staticmethod
    def from_template(fileurl:str) -> 'Environments': ...

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

        definition_rsp = HttpSource(definition_url).read()

        if definition_rsp.status_code == 404:
            root_dir_text = HttpSource("https://api.github.com/repos/mrucker/coba_prebuilds/contents/").read().content.decode('utf-8')
            root_dir_json = JsonDecode().filter(root_dir_text)
            known_names   = [ obj['name'] for obj in root_dir_json if obj['name'] != "README.md" ]
            raise CobaException(f"The given prebuilt name, {name}, couldn't be found. Known names are: {known_names}")

        definition_txt = definition_rsp.content.decode('utf-8')
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
        take: int = None) -> 'Environments':
        ...

    @overload
    @staticmethod
    def from_openml(*,task_id: Union[int,Sequence[int]],
        drop_missing: bool = True,
        take: int = None) -> 'Environments':
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

    def __init__(self, *environments: Union[Environment, Sequence[Environment]]):
        """Instantiate an Environments class.

        Args:
            *environments: The base environments to initialize the class.
        """
        self._environments = []

        for env in environments:
            if isinstance(env, collections.abc.Sequence):
                self._environments.extend(env)
            else:
                self._environments.append(env)

    def binary(self) -> 'Environments':
        """Binarize all rewards to either 1 (max rewards) or 0 (all others)."""
        return self.filter(Binary())

    def sparse(self, context:bool = True, action:bool = False) -> 'Environments':
        """Convert an environment from a dense representation to sparse. This has little utility beyond debugging."""
        return self.filter(Sparse(context,action))

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

        if kwargs:
            seeds = range(kwargs['n'])
        else:
            seeds = flat(args) or [1]
                
        if isinstance(seeds,int): seeds = [seeds]
        return self.filter([Shuffle(seed) for seed in seeds])

    def sort(self, *keys: Union[str,int,Sequence[Union[str,int]]]) -> 'Environments':
        """Sort Environment interactions according to the context values indicated by keys."""
        return self.filter(Sort(*keys))

    def riffle(self, spacing: int, seed: int = 1) -> 'Environments':
        """Riffle shuffle by evenly spacing interactions at the end of an environment into the beginning."""
        return self.filter(Riffle(spacing, seed))

    def cycle(self, after: int) -> 'Environments':
        """Cycle all rewards associated with actions by one place."""
        return self.filter(Cycle(after))

    def params(self, params: Mapping[str,Any]) -> 'Environments':
        """Add params to the environments."""
        return self.filter(Params(params))

    def take(self, n_interactions: int) -> 'Environments':
        """Take a fixed number of interactions from the Environments."""
        return self.filter(Take(n_interactions))

    def reservoir(self, n_interactions: int, seeds: Union[int,Sequence[int]]) -> 'Environments':
        """Take a random fixed number of interactions from the Environments."""
        if isinstance(seeds,int): seeds = [seeds]
        return self.filter([Reservoir(n_interactions,seed) for seed in seeds])

    def scale(self,
        shift: Union[float,Literal["min","mean","med"]] = "min",
        scale: Union[float,Literal["minmax","std","iqr","maxabs"]] = "minmax",
        target: Literal["context","rewards","argmax"] = "context",
        using: Optional[int] = None) -> 'Environments':
        """Apply an affine shift and scaling factor to precondition environments."""
        return self.filter(Scale(shift, scale, target, using))

    def impute(self,
        stat : Literal["mean","median","mode"] = "mean",
        using: Optional[int] = None) -> 'Environments':
        """Impute missing values with a feature statistic using a given number of interactions."""
        return self.filter(Impute(stat, using))

    def where(self,*,n_interactions: Union[int,Tuple[Optional[int],Optional[int]]] = None) -> 'Environments':
        """Only include environments which satisify the given requirements."""
        return self.filter(Where(n_interactions=n_interactions))

    def noise(self,
        context: Callable[[float,CobaRandom], float] = None,
        action : Callable[[float,CobaRandom], float] = None,
        reward : Callable[[float,CobaRandom], float] = None,
        seed   : int = 1) -> 'Environments':
        """Add noise to an environment's context, actions and rewards."""
        return Environments(*self).filter(Noise(context,action,reward,seed))

    def flat(self) -> 'Environments':
        """Flatten environment's context and actions."""
        return self.filter(Flatten())

    def materialize(self) -> 'Environments':
        """Materialize the environments in memory. Ideal for stateful environments such as Jupyter Notebook."""
        envs = self.cache()
        for env in envs: list(env.read()) #force read to pre-load cache
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

    def cache(self) -> 'Environments':
        """Create a cache point in the environments so that earlier steps in the pipeline can be re-used in several pipes."""
        return Environments([Pipes.join(env, Cache(2)) for env in self])

    def filter(self, filter: Union[EnvironmentFilter,Sequence[EnvironmentFilter]]) -> 'Environments':
        """Apply filters to each environment currently in Environments."""
        filters = filter if isinstance(filter, collections.abc.Sequence) else [filter]
        return Environments([Pipes.join(e,f) for e in self._environments for f in filters])

    def __getitem__(self, index:int) -> Environment:
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
