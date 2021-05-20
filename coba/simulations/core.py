from abc import ABC, abstractmethod
from itertools import accumulate, repeat
from typing import Optional, Sequence, List, Callable, Hashable, Tuple, Dict, Any, Union, Iterable

import coba.random
from coba.encodings import OneHotEncoder
from coba.pipes import Pipe, CsvReader, ResponseToLines, Transpose, Source, DiskSource, HttpSource

Action      = Hashable
Key         = int
Context     = Optional[Hashable]

class Interaction:
    """A class to contain all data needed to represent an interaction in a bandit simulation."""

    def __init__(self, key: Key, context: Context, actions: Sequence[Action]) -> None:
        """Instantiate Interaction.

        Args
            context: Features describing the interaction's context. Will be `None` for multi-armed bandit simulations.
            actions: Features describing available actions in the interaction.
            key    : A unique key assigned to this interaction.
        """

        assert actions, "At least one action must be provided to interact"

        self._key     = key
        self._context = context
        self._actions = actions

    @property
    def key(self) -> Key:
        """A unique key identifying the interaction."""
        return self._key

    @property
    def context(self) -> Optional[Context]:
        """The interaction's context description."""
        return self._context

    @property
    def actions(self) -> Sequence[Action]:
        """The interaction's available actions."""
        return self._actions

class Simulation(ABC):
    """The simulation interface."""

    @property
    @abstractmethod
    def interactions(self) -> Sequence[Interaction]:
        """The sequence of interactions in a simulation.

        Remarks:
            Interactions should always be re-iterable. So long as interactions is a Sequence 
            this will always be the case. If interactions is changed to Iterable in the future
            then it will be possible for it to only allow enumeration one time and care will need
            to be taken.
        """
        ...

    @property
    @abstractmethod
    def reward(self) -> 'Reward':
        """The reward object which can observe rewards for pairs of actions and interaction keys."""
        ...    

class Reward(ABC):

    @abstractmethod
    def observe(self, choices: Sequence[Tuple[Key,Context,Action]] ) -> Sequence[float]:
        ...

class MemoryReward(Reward):
    def __init__(self, rewards: Sequence[Tuple[Key,Action,float]] = []) -> None:
        self._rewards: Dict[Tuple[Key,Action], float] = { (r[0],r[1]):r[2] for r in rewards }

    def observe(self, choices: Sequence[Tuple[Key,Context,Action]] ) -> Sequence[float]:
        return [ self._rewards[(key,action)] for key,_,action in choices ]

class ClassificationReward(Reward):
    def __init__(self, labels: Sequence[Tuple[Key,Action]] = []) -> None:
        self._labels = dict(labels)

    def add(self, key: Key, action: Action):
        self._labels[key] = action

    def observe(self, choices: Sequence[Tuple[Key,Context,Action]] ) -> Sequence[float]:
        return [ float(self._labels[key] == action) for key, _, action in choices ]

class MemorySimulation(Simulation):
    """A Simulation implementation created from in memory sequences of contexts, actions and rewards."""

    def __init__(self, interactions: Sequence[Interaction], reward: Reward) -> None:
        """Instantiate a MemorySimulation.

        Args:
            interactions: The sequence of interactions in this simulation.
            reward: The reward object to observe in this simulation.
        """

        self._interactions = interactions
        self._reward       = reward

    @property
    def interactions(self) -> Sequence[Interaction]:
        """The interactions in this simulation.

        Remarks:
            See the Simulation base class for more information.
        """
        return self._interactions

    @property
    def reward(self) -> Reward:
        """The reward object which can observe rewards for pairs of actions and interaction keys."""
        return self._reward

class ClassificationSimulation(MemorySimulation):
    """A simulation created from classification dataset with features and labels.

    ClassificationSimulation turns labeled observations from a classification data set
    into interactions. For each interaction the feature set becomes the context and 
    all possible labels become the actions. Rewards for each interaction are created by 
    assigning a reward of 1 for taking the correct action (i.e., choosing the correct
    label)) and a reward of 0 for taking any other action (i.e., choosing any of the
    incorrect lables).

    Remark:
        This class when created from a data set will load all data into memory. Be careful when 
        doing this if you are working with a large dataset. To reduce memory usage you can provide
        meta information upfront that will allow features to be correctly encoded while the
        dataset is being streamed instead of waiting until the end of the data to train an encoder.
    """

    def __init__(self, features: Sequence[Any], labels: Sequence[Action]) -> None:
        """Instantiate a ClassificationSimulation.

        Args:
            features: The collection of features used for the original classifier problem.
            labels: The collection of labels assigned to each observation of features.
        """

        assert len(features) == len(labels), "Mismatched lengths of features and labels"

        self.one_hot_encoder = OneHotEncoder(list(sorted(set(labels), key=lambda i: labels.index(i))))

        labels     = self.one_hot_encoder.encode(labels)
        action_set = list(sorted(set(labels), reverse=True))

        print(labels)

        interactions = [ Interaction(i, context, action_set) for i, context in enumerate(features) ] #type: ignore
        reward       = ClassificationReward(list(enumerate(labels)))

        super().__init__(interactions, reward) #type:ignore

class BatchedSimulation(MemorySimulation):
    """A simulation whose interactions have been batched."""

    def __init__(self, simulation: Simulation, batch_sizes: Sequence[int]) -> None:
        self._simulation = simulation

        #remove Nones and 0s
        batch_sizes  = list(filter(None, batch_sizes))
        batch_slices = list(accumulate([0] + list(batch_sizes)))

        self._batches = [ simulation.interactions[batch_slices[i]:batch_slices[i+1]] for i in range(len(batch_slices)-1) ]

        super().__init__(simulation.interactions[0:sum(batch_sizes)], simulation.reward)

    @property
    def interaction_batches(self) -> Sequence[Sequence[Interaction]]:
        """The sequence of batches of interactions in a simulation."""
        return self._batches

class LambdaSimulation(Source[Simulation]):
    """A Simulation created from lambda functions that generate contexts, actions and rewards.

    Remarks:
        This implementation is useful for creating simulations from defined distributions.
    """

    def __init__(self,
        n_interactions: int,
        context       : Callable[[int               ],Context         ],
        actions       : Callable[[int,Context       ],Sequence[Action]], 
        reward        : Callable[[int,Context,Action],float           ],
        seed          : int = None) -> None:
        """Instantiate a LambdaSimulation.

        Args:
            n_interactions: How many interactions the LambdaSimulation should have.
            context: A function that should return a context given an index in `range(n_interactions)`.
            actions: A function that should return all valid actions for a given index and context.
            reward: A function that should return the reward for the index, context and action.
        """

        coba.random.seed(seed)

        interaction_tuples: List[Tuple[Key, Context, Sequence[Action]]] = []
        reward_tuples     : List[Tuple[Key, Action , float           ]] = []

        for i in range(n_interactions):
            _context  = context(i)
            _actions  = actions(i,_context)
            _rewards  = [ reward(i, _context, _action) for _action in _actions]

            interaction_tuples.append( (i, _context, _actions) )
            reward_tuples.extend(zip(repeat(i), _actions, _rewards))

        self._interactions = [ Interaction(key, context, actions) for key,context,actions in interaction_tuples ]
        self._reward       = MemoryReward(reward_tuples)
        self._simulation   = MemorySimulation(self._interactions, self._reward)

    def read(self) -> Simulation:
        return self._simulation

    def __repr__(self) -> str:
        return '"LambdaSimulation"'

class CsvSimulation(Source[Simulation]):

    def __init__(self, csv_source:Union[str,Source[Iterable[str]]], label_column:Union[str,int], with_header:bool=True) -> None:
        
        if isinstance(csv_source, str) and csv_source.startswith('http'):
            self._csv_source = Pipe.join(HttpSource(csv_source), [ResponseToLines()])
        elif isinstance(csv_source, str):
            self._csv_source = DiskSource(csv_source)
        else:
            self._csv_source = csv_source
        
        self._label_column = label_column
        self._with_header  = with_header

    def read(self) -> Simulation:
        parsed_rows_iter = iter(CsvReader().filter(self._csv_source.read()))

        if self._with_header:
            header = next(parsed_rows_iter)
        else:
            header = []

        if isinstance(self._label_column, str):
            label_col_index = header.index(self._label_column)
        else:
            label_col_index = self._label_column

        parsed_cols = list(Transpose().filter(parsed_rows_iter))
        
        label_col    = parsed_cols.pop(label_col_index)
        feature_rows = list(Transpose().filter(parsed_cols))

        return ClassificationSimulation(feature_rows, label_col)
