
import collections

from itertools import product
from typing import Sequence, Dict, Any

from coba.registry import CobaRegistry
from coba.pipes import Filter
from coba.simulations import SimSourceFilters

from coba.benchmarks.core import Benchmark

class BenchmarkFileFmtV2(Filter[Dict[str,Any], Benchmark]):

    def filter(self, config: Dict[str,Any]) -> 'Benchmark':

        variables = { k: CobaRegistry.construct(v) for k,v in config.get("variables",{}).items() }

        def _construct(item:Any) -> Sequence[Any]:
            result = None

            if isinstance(item, str) and item in variables:
                result = variables[item]

            if isinstance(item, str) and item not in variables:
                result = CobaRegistry.construct(item)

            if isinstance(item, dict):
                result = CobaRegistry.construct(item)

            if isinstance(item, list):
                pieces = list(map(_construct, item))
                
                if hasattr(pieces[0][0],'read'):
                    result = [ SimSourceFilters(s, f) for s in pieces[0] for f in product(*pieces[1:])]
                else:
                    result = sum(pieces,[])

            if result is None:
                raise Exception(f"We were unable to construct {item} in the given benchmark file.")

            return result if isinstance(result, collections.Sequence) else [result]

        if not isinstance(config['simulations'], list): config['simulations'] = [config['simulations']]

        simulations = [ simulation for recipe in config['simulations'] for simulation in _construct(recipe)]

        return Benchmark(simulations)
