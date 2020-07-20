from typing import List
import unittest

from math import isnan

from coba.simulations import LambdaSimulation, LazySimulation, Simulation
from coba.learners import LambdaLearner
from coba.benchmarks import Stats, Result, UniversalBenchmark

class Stats_Tests(unittest.TestCase):
    def test_from_values_multi_mean_is_correct_1(self):
        stats = Stats.from_values([1,1,3,3])
        self.assertEqual(2,stats.mean)

    def test_from_values_multi_mean_is_correct_2(self):
        stats = Stats.from_values([1,1,1,1])
        self.assertEqual(1,stats.mean)

    def test_from_values_single_mean_is_correct(self):
        stats = Stats.from_values([3])
        self.assertEqual(3,stats.mean)

    def test_from_values_empty_mean_is_correct(self):
        stats = Stats.from_values([])
        self.assertTrue(isnan(stats.mean))

class Result_Tests(unittest.TestCase):
    def test_batch_means1(self):
        result = Result([(1,1,3), (1,1,4), (1,2,5), (1,2,5), (1,3,6)])

        self.assertEqual(len(result.batch_stats),3)

        self.assertAlmostEqual((3.+4.)/2., result.batch_stats[0].mean)
        self.assertAlmostEqual((5+5  )/2, result.batch_stats[1].mean)
        self.assertAlmostEqual((6    )/1, result.batch_stats[2].mean)

    def test_batch_means2(self):
        result = Result([(1,1,3), (1,1,4), (1,2,5), (1,2,5), (1,3,6), (2,1,3)])

        self.assertEqual(len(result.batch_stats),3)

        self.assertAlmostEqual((3+4+3)/3, result.batch_stats[0].mean)
        self.assertAlmostEqual((5+5  )/2, result.batch_stats[1].mean)
        self.assertAlmostEqual((6    )/1, result.batch_stats[2].mean)

    def test_cumulative_batch_means1(self):
        result = Result([(1,1,3), (1,1,4), (1,2,5), (1,2,5), (1,3,6)])

        self.assertEqual(len(result.cumulative_batch_stats),3)

        self.assertAlmostEqual((3+4      )/2, result.cumulative_batch_stats[0].mean)
        self.assertAlmostEqual((3+4+5+5  )/4, result.cumulative_batch_stats[1].mean)
        self.assertAlmostEqual((3+4+5+5+6)/5, result.cumulative_batch_stats[2].mean)

    def test_cumulative_batch_means2(self):
        result = Result([(1,1,3), (1,1,4), (1,2,5), (1,2,5), (1,3,6), (2,1,3)])

        self.assertEqual(len(result.cumulative_batch_stats),3)

        self.assertAlmostEqual((3+4+3      )/3, result.cumulative_batch_stats[0].mean)
        self.assertAlmostEqual((3+4+3+5+5  )/5, result.cumulative_batch_stats[1].mean)
        self.assertAlmostEqual((3+4+3+5+5+6)/6, result.cumulative_batch_stats[2].mean)

    def test_predicate_means1(self):
        result = Result([(1,1,3), (1,1,4), (1,2,5), (1,2,5), (1,3,6)])

        actual_mean = result.predicate_stats(lambda o: o[1]==1).mean
        expected_mean = (3+4)/2

        self.assertAlmostEqual(actual_mean, expected_mean)

    def test_predicate_means2(self):
        result = Result([(1,1,3), (1,1,4), (1,2,5), (1,2,5), (1,3,6)])

        actual_mean = result.predicate_stats(lambda o: o[1]==1 or o[1]==3).mean
        expected_mean = (3+4+6)/3

        self.assertAlmostEqual(actual_mean, expected_mean)

class UniversalBenchmark_Tests(unittest.TestCase):

    def test_from_json(self):
        json = """{
            "batches": 1,
            "simulations": [
                {"seed":1283,"type":"classification","from":{"format":"openml","id":1116}},
                {"seed":1283,"type":"classification","from":{"format":"openml","id":1116}}
            ]
        }"""

        benchmark = UniversalBenchmark.from_json(json)

        self.assertEqual(len(benchmark._simulations),2)
        self.assertIsInstance(benchmark._simulations[0],LazySimulation)

    def test_one_sim_five_batches_of_one(self):
        sim             = LambdaSimulation[int,int](50, lambda i: i, lambda s: [0,1,2], lambda s, a: a)
        learner_factory = lambda: LambdaLearner[int,int](lambda s, A: int(s%3))
        benchmark       = UniversalBenchmark[int,int]([sim], [1]*5)

        result = benchmark.evaluate([learner_factory])[0]

        expected_observations = [
            (0,0,0),(0,1,1),(0,2,2),(0,3,0),(0,4,1)
        ]

        self.assertEqual(result.observations, expected_observations)

    def test_one_sim_one_batch_of_five(self):
        sim             = LambdaSimulation(50, lambda i: i, lambda s: [0,1,2], lambda s,a: a)
        learner_factory = lambda: LambdaLearner[int,int](lambda s,A: A[int(s%3)])
        benchmark       = UniversalBenchmark([sim], [5])

        result = benchmark.evaluate([learner_factory])[0]

        expected_observations = [
            (0,0,0),(0,0,1),(0,0,2),(0,0,0),(0,0,1)
        ]

        self.assertEqual(result.observations, expected_observations)

    def test_one_sim_three_batches_of_three(self):
        sim             = LambdaSimulation(50, lambda i: i, lambda s: [0,1,2], lambda s, a: a)
        learner_factory = lambda: LambdaLearner[int,int](lambda s, A: int(s%3))
        benchmark       = UniversalBenchmark([sim], [3,3,3])

        result = benchmark.evaluate([learner_factory])[0]

        expected_observations = [
            (0,0,0),(0,0,1),(0,0,2),(0,1,0),(0,1,1),(0,1,2),(0,2,0),(0,2,1),(0,2,2)
        ]

        self.assertEqual(result.observations, expected_observations)

    def test_one_sim_two_batches(self):
        sim            = LambdaSimulation(50, lambda i: i, lambda s: [0,1,2], lambda s,a: a)
        learner_factory = lambda: LambdaLearner[int,int](lambda s, A: s%3)
        benchmark       = UniversalBenchmark([sim], [4,2])

        result = benchmark.evaluate([learner_factory])[0]

        expected_observations = [
            (0,0,0),(0,0,1),(0,0,2),(0,0,0),(0,1,1),(0,1,2)
        ]

        self.assertEqual(result.observations, expected_observations)

    def test_one_sim_four_batches(self):
        sim            = LambdaSimulation(50, lambda i: i, lambda s: [0,1,2], lambda s,a: a)
        learner_factory = lambda: LambdaLearner[int,int](lambda s,A: int(s%3))
        benchmark       = UniversalBenchmark([sim], [1, 2, 4, 1])

        result = benchmark.evaluate([learner_factory])[0]

        expected_observations = [
            (0,0,0),(0,1,1),(0,1,2),(0,2,0),(0,2,1),(0,2,2),(0,2,0),(0,3,1)
        ]

        self.assertEqual(result.observations, expected_observations)

    def test_two_sims_five_batches_of_one(self):
        sim1            = LambdaSimulation(50, lambda i: i, lambda s: [0,1,2], lambda s,a: a)
        sim2            = LambdaSimulation(50, lambda i: i, lambda s: [3,4,5], lambda s,a: a)
        learner_factory = lambda: LambdaLearner[int,int](lambda s,A: int(s%3))
        benchmark       = UniversalBenchmark([sim1,sim2], [1]*5)

        result = benchmark.evaluate([learner_factory])[0]

        expected_observations = [
            (0,0,0),(0,1,1),(0,2,2),(0,3,0),(0,4,1),
            (1,0,3),(1,1,4),(1,2,5),(1,3,3),(1,4,4)
        ]

        self.assertEqual(result.observations, expected_observations)

    def test_two_sims_one_batch_of_five(self):
        sim1            = LambdaSimulation(50, lambda i: i, lambda s: [0,1,2], lambda s,a: a)
        sim2            = LambdaSimulation(50, lambda i: i, lambda s: [3,4,5], lambda s,a: a)
        learner_factory = lambda: LambdaLearner[int,int](lambda s,A: int(s%3))
        benchmark       = UniversalBenchmark([sim1,sim2], [5])

        result = benchmark.evaluate([learner_factory])[0]

        expected_observations = [
            (0,0,0),(0,0,1),(0,0,2),(0,0,0),(0,0,1),
            (1,0,3),(1,0,4),(1,0,5),(1,0,3),(1,0,4)
        ]

        self.assertEqual(result.observations, expected_observations)

    def test_two_sims_three_batches_of_three(self):
        sim1            = LambdaSimulation(50, lambda i: i, lambda s: [0,1,2], lambda s, a: a)
        sim2            = LambdaSimulation(50, lambda i: i, lambda s: [3,4,5], lambda s, a: a)
        learner_factory = lambda: LambdaLearner[int,int](lambda s, A: int(s%3))

        benchmark       = UniversalBenchmark[int,int]([sim1,sim2], [3]*3)

        result = benchmark.evaluate([learner_factory])[0]

        expected_observations = [
            (0,0,0),(0,0,1),(0,0,2),(0,1,0),(0,1,1),(0,1,2),(0,2,0),(0,2,1),(0,2,2),
            (1,0,3),(1,0,4),(1,0,5),(1,1,3),(1,1,4),(1,1,5),(1,2,3),(1,2,4),(1,2,5)
        ]

        self.assertEqual(result.observations, expected_observations)

    def test_two_sims_two_batches_of_four_and_two(self):
        sim1            = LambdaSimulation(50, lambda i: i, lambda s: [0,1,2], lambda s, a: a)
        sim2            = LambdaSimulation(50, lambda i: i, lambda s: [3,4,5], lambda s, a: a)
        learner_factory = lambda: LambdaLearner[int,int](lambda s, A: int(s%3))
        benchmark       = UniversalBenchmark([sim1,sim2], [4,2])

        result = benchmark.evaluate([learner_factory])[0]

        expected_observations = [
            (0,0,0),(0,0,1),(0,0,2),(0,0,0),(0,1,1),(0,1,2),
            (1,0,3),(1,0,4),(1,0,5),(1,0,3),(1,1,4),(1,1,5)
        ]

        self.assertEqual(result.observations, expected_observations)

    def test_lazy_sim_two_batches(self):
        sim1            = LazySimulation[int,int](lambda:LambdaSimulation(50, lambda i: i, lambda s: [0,1,2], lambda s, a: a))
        benchmark       = UniversalBenchmark([sim1], [4,2])
        learner_factory = lambda: LambdaLearner[int,int](lambda s, A: int(s%3))
        result = benchmark.evaluate([learner_factory])[0]

        expected_observations = [
            (0,0,0),(0,0,1),(0,0,2),(0,0,0),(0,1,1),(0,1,2)
        ]

        self.assertEqual(result.observations, expected_observations)

if __name__ == '__main__':
    unittest.main()