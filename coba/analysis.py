"""The analysis module contains functionality to help with analyzing Results."""

from collections import defaultdict
from itertools import groupby
from typing import Callable, Tuple, List, Dict, Any, Hashable

from coba.statistics import StatisticalEstimate, Aggregator
from coba.utilities import check_matplotlib_support
from coba.benchmarks import Result

class Plots():

    @staticmethod
    def standard_plot(result: Result) -> None:

        def plot_stats(axes, label, stats):
            x = [ i+1                          for i in range(len(stats)) ]
            y = [ s.estimate                   for s in stats             ]
            l = [ s.estimate-s.standard_error  for s in stats             ]
            u = [ s.estimate+s.standard_error  for s in stats             ]

            axes.plot(x,y, label=label)
            axes.fill_between(x, l, u, alpha = 0.25)

        learners, _, performances = result.to_indexed_tuples()

        sorted_performances  = sorted(performances.values(), key=lambda r: (r.learner_id, r.batch_id))
        grouped_performances = groupby(sorted_performances, key=lambda r: (r.learner_id, r.batch_id))

        learner_stats: Dict[str,List[StatisticalEstimate]] = defaultdict(list)

        for batch_group in grouped_performances:
            learner_name = learners[batch_group[0][0]].name
            mean_rewards = [performance.mean_reward for performance in batch_group[1]]
            mean_reward  = Aggregator.weighted_mean(mean_rewards)
            learner_stats[learner_name].append(mean_reward)

        check_matplotlib_support('Plots.standard_plot')
        import matplotlib.pyplot as plt #type: ignore

        fig = plt.figure()

        ax1 = fig.add_subplot(1,2,1) #type: ignore
        ax2 = fig.add_subplot(1,2,2) #type: ignore

        for learner_name, stats in learner_stats.items():
            plot_stats(ax1, learner_name, stats)

        ax1.set_title("Reward by Batch Index")
        ax1.set_ylabel("Mean Reward")
        ax1.set_xlabel("Batch Index")

        for learner_name, stats in learner_stats.items(): 
            plot_stats(ax2, learner_name, [ Aggregator.weighted_mean(stats[0:i+1]) for i in range(len(stats)) ])

        ax2.set_title("Progressive Validation Reward")
        ax2.set_xlabel("Batch Index")

        (bot1, top1) = ax1.get_ylim()
        (bot2, top2) = ax2.get_ylim()

        ax1.set_ylim(min(bot1,bot2), max(top1,top2))
        ax2.set_ylim(min(bot1,bot2), max(top1,top2))

        scale = 0.25
        box1 = ax1.get_position()
        box2 = ax2.get_position()
        ax1.set_position([box1.x0, box1.y0 + box1.height * scale, box1.width, box1.height * (1-scale)])
        ax2.set_position([box2.x0, box2.y0 + box2.height * scale, box2.width, box2.height * (1-scale)])

        # Put a legend below current axis
        fig.legend(*ax1.get_legend_handles_labels(), loc='upper center', bbox_to_anchor=(.5, .175), fancybox=True, ncol=3) #type: ignore

        plt.show()