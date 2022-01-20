import importlib.util
import unittest
import unittest.mock

from typing import Sequence, cast

from coba.utilities import KeyDefaultDict
from coba.exceptions import CobaException
from coba.learners import VowpalMediator
from coba.learners import (
    VowpalArgsLearner, VowpalEpsilonLearner, VowpalSoftmaxLearner,
    VowpalBagLearner, VowpalCoverLearner, VowpalRegcbLearner,
    VowpalSquarecbLearner, VowpalOffPolicyLearner
)

class VowpalExampleMock:

    def __init__(self,ns,label):
        self.ns         = ns
        self.label      = label

class VowpalMediatorMock:

    def __init__(self, predict_returns = None) -> None:
        self._init_learner_calls  = []
        self._predict_calls       = []
        self._learn_calls         = []
        self._make_example_calls  = []
        self._make_examples_calls = []
        self._predict_returns     = predict_returns

    @property
    def is_initialized(self):
        return len(self._init_learner_calls) > 0

    def init_learner(self, args:str, label_type: int):
        self._init_learner_calls.append((args, label_type))

    def predict(self, example):
        self._predict_calls.append(example)
        return self._predict_returns

    def learn(self, example):
        self._learn_calls.append(example)

    def make_example(self, namespaces, label):
        return VowpalExampleMock(namespaces,label)

    def make_examples(self, shared, distincts, labels):
        if labels is None: labels = [None]*len(distincts)
        return [ VowpalExampleMock((shared,d),l) for d,l in zip(distincts,labels)]

class VowpalEpsilonLearner_Tests(unittest.TestCase):

    @unittest.mock.patch('coba.learners.vowpal.VowpalArgsLearner.__init__')
    def test_defaults(self, mock) -> None:
        VowpalEpsilonLearner()
        mock.assert_called_once_with("--cb_explore_adf --epsilon 0.05 --interactions xxa --interactions xa --ignore_linear x --random_seed 1")

    @unittest.mock.patch('coba.learners.vowpal.VowpalArgsLearner.__init__')
    def test_specifics(self, mock) -> None:
        VowpalEpsilonLearner(epsilon=0.1, interactions=["xa"], ignore_linear=[], seed=None)
        mock.assert_called_once_with("--cb_explore_adf --epsilon 0.1 --interactions xa")

    @unittest.mock.patch('coba.learners.vowpal.VowpalArgsLearner.__init__')
    def test_custom_flag(self, mock) -> None:
        VowpalEpsilonLearner(epsilon=0.1, interactions=["xa"], ignore_linear=[], seed=None, b=20)
        mock.assert_called_once_with("--cb_explore_adf --epsilon 0.1 --interactions xa -b 20")

class VowpalSoftmaxLearner_Tests(unittest.TestCase):
    
    @unittest.mock.patch('coba.learners.vowpal.VowpalArgsLearner.__init__')
    def test_defaults(self, mock) -> None:
        VowpalSoftmaxLearner()
        mock.assert_called_once_with("--cb_explore_adf --softmax --lambda 10 --interactions xxa --interactions xa --ignore_linear x --random_seed 1")

    @unittest.mock.patch('coba.learners.vowpal.VowpalArgsLearner.__init__')
    def test_specifics(self, mock) -> None:
        VowpalSoftmaxLearner(softmax=5, interactions=["xa"], ignore_linear=[], seed=None)
        mock.assert_called_once_with("--cb_explore_adf --softmax --lambda 5 --interactions xa")

class VowpalSoftmaxLearner_Tests(unittest.TestCase):

    @unittest.mock.patch('coba.learners.vowpal.VowpalArgsLearner.__init__')
    def test_defaults(self, mock) -> None:
        VowpalSoftmaxLearner()
        mock.assert_called_once_with("--cb_explore_adf --softmax --lambda 10 --interactions xxa --interactions xa --ignore_linear x --random_seed 1")

    @unittest.mock.patch('coba.learners.vowpal.VowpalArgsLearner.__init__')
    def test_specifics(self, mock) -> None:
        VowpalSoftmaxLearner(softmax=5, interactions=["xa"], ignore_linear=[], seed=None)
        mock.assert_called_once_with("--cb_explore_adf --softmax --lambda 5 --interactions xa")

class VowpalBagLearner_Tests(unittest.TestCase):

    @unittest.mock.patch('coba.learners.vowpal.VowpalArgsLearner.__init__')
    def test_defaults(self, mock) -> None:
        VowpalBagLearner()
        mock.assert_called_once_with("--cb_explore_adf --bag 5 --interactions xxa --interactions xa --ignore_linear x --random_seed 1")

    @unittest.mock.patch('coba.learners.vowpal.VowpalArgsLearner.__init__')
    def test_specifics(self, mock) -> None:
        VowpalBagLearner(bag=10, interactions=["xa"], ignore_linear=[], seed=None)
        mock.assert_called_once_with("--cb_explore_adf --bag 10 --interactions xa")

class VowpalCoverLearner_Tests(unittest.TestCase):

    @unittest.mock.patch('coba.learners.vowpal.VowpalArgsLearner.__init__')
    def test_defaults(self, mock) -> None:
        VowpalCoverLearner()
        mock.assert_called_once_with("--cb_explore_adf --cover 5 --interactions xxa --interactions xa --ignore_linear x --random_seed 1")

    @unittest.mock.patch('coba.learners.vowpal.VowpalArgsLearner.__init__')
    def test_specifics(self, mock) -> None:
        VowpalCoverLearner(cover=10, interactions=["xa"], ignore_linear=[], seed=None)
        mock.assert_called_once_with("--cb_explore_adf --cover 10 --interactions xa")

class VowpalRegcbLearner_Tests(unittest.TestCase):

    @unittest.mock.patch('coba.learners.vowpal.VowpalArgsLearner.__init__')
    def test_defaults(self, mock) -> None:
        VowpalRegcbLearner()
        mock.assert_called_once_with("--cb_explore_adf --regcb --interactions xxa --interactions xa --ignore_linear x --random_seed 1")

    @unittest.mock.patch('coba.learners.vowpal.VowpalArgsLearner.__init__')
    def test_specifics(self, mock) -> None:
        VowpalRegcbLearner(mode="optimistic", interactions=["xa"], ignore_linear=[], seed=None)
        mock.assert_called_once_with("--cb_explore_adf --regcbopt --interactions xa")

class VowpalSquarecbLearner_Tests(unittest.TestCase):

    @unittest.mock.patch('coba.learners.vowpal.VowpalArgsLearner.__init__')
    def test_defaults(self, mock) -> None:
        VowpalSquarecbLearner()
        mock.assert_called_once_with("--cb_explore_adf --squarecb --gamma_scale 10 --interactions xxa --interactions xa --ignore_linear x --random_seed 1")

    @unittest.mock.patch('coba.learners.vowpal.VowpalArgsLearner.__init__')
    def test_specifics(self, mock) -> None:
        VowpalSquarecbLearner(mode="elimination", gamma_scale=5, interactions=["xa"], ignore_linear=[], seed=None)
        mock.assert_called_once_with("--cb_explore_adf --squarecb --gamma_scale 5 --elim --interactions xa")

class VowpalOffpolicyLearner_Tests(unittest.TestCase):

    @unittest.mock.patch('coba.learners.vowpal.VowpalArgsLearner.__init__')
    def test_defaults(self, mock) -> None:
        VowpalOffPolicyLearner()
        mock.assert_called_once_with("--cb_adf --interactions xxa --interactions xa --ignore_linear x --random_seed 1")

    @unittest.mock.patch('coba.learners.vowpal.VowpalArgsLearner.__init__')
    def test_specifics(self, mock) -> None:
        VowpalOffPolicyLearner(interactions=["xa"], ignore_linear=[], seed=None)
        mock.assert_called_once_with("--cb_adf --interactions xa")

class VowpalArgsLearner_Tests(unittest.TestCase):

    def test_params(self):

        learners = VowpalArgsLearner()

        expected_args = [
            "--cb_explore_adf",
            "--epsilon 0.05",
            "--interactions xxa",
            "--interactions xa",
            "--ignore_linear x",
            "--random_seed 1",
        ]

        self.assertEqual(learners.params['family'], "vw")
        self.assertEqual(learners.params["args"], " ".join(expected_args))

    def test_init_bad(self):
        with self.assertRaises(CobaException):
            VowpalArgsLearner('--epsilon .1')

    def test_init_learner_default(self):

        vw = VowpalMediatorMock()
        VowpalArgsLearner(vw=vw).predict(None, ['yes','no'])

        expected_args = [
            "--cb_explore_adf",
            "--epsilon 0.05",
            "--interactions xxa",
            "--interactions xa",
            "--ignore_linear x",
            "--random_seed 1",
            "--quiet"
        ]

        self.assertEqual((" ".join(expected_args), 4), vw._init_learner_calls[0])

    def test_init_learner_cb_explore_adf(self):
        vw = VowpalMediatorMock()
        VowpalArgsLearner("--cb_explore_adf", vw).predict(None, ['yes','no'])

        self.assertEqual(("--cb_explore_adf --quiet", 4), vw._init_learner_calls[0])

    def test_init_learner_cb_adf(self):

        vw = VowpalMediatorMock([0.25,0.75])
        VowpalArgsLearner("--cb_adf",vw).predict(None, ['yes','no'])

        self.assertEqual(("--cb_adf --quiet", 4), vw._init_learner_calls[0])

    def test_init_learner_cb_explore(self):
        vw = VowpalMediatorMock()
        
        VowpalArgsLearner("--cb_explore 20", vw).predict(None, ['yes','no'])

        self.assertEqual(("--cb_explore 2 --quiet", 4), vw._init_learner_calls[0])

    def test_init_learner_cb(self):
        vw = VowpalMediatorMock(1)
        VowpalArgsLearner("--cb 20", vw).predict(None, ['yes','no'])

        self.assertEqual(("--cb 2 --quiet", 4), vw._init_learner_calls[0])

    def test_predict_cb_explore_adf(self):

        vw = VowpalMediatorMock([.25, .75])
        p = VowpalArgsLearner("--cb_explore_adf",vw).predict(None, ['yes','no'])[0]

        self.assertEqual(2, len(vw._predict_calls[0]))

        self.assertEqual({'x':None }, vw._predict_calls[0][0].ns[0])
        self.assertEqual({'a':'yes'}, vw._predict_calls[0][0].ns[1])
        self.assertEqual(None       , vw._predict_calls[0][0].label)

        self.assertEqual({'x':None }, vw._predict_calls[0][1].ns[0])
        self.assertEqual({'a':'no'} , vw._predict_calls[0][1].ns[1])
        self.assertEqual(None       , vw._predict_calls[0][1].label)

        self.assertEqual([.25, .75], p)

    def test_predict_cb_adf(self):

        vw = VowpalMediatorMock([.25, .75])
        p  = VowpalArgsLearner("--cb_adf",vw).predict(None, ['yes','no'])[0]

        self.assertEqual(2, len(vw._predict_calls[0]))

        self.assertEqual({'x':None }, vw._predict_calls[0][0].ns[0])
        self.assertEqual({'a':'yes'}, vw._predict_calls[0][0].ns[1])
        self.assertEqual(None       , vw._predict_calls[0][0].label)

        self.assertEqual({'x':None }, vw._predict_calls[0][1].ns[0])
        self.assertEqual({'a':'no'} , vw._predict_calls[0][1].ns[1])
        self.assertEqual(None       , vw._predict_calls[0][1].label)

        self.assertEqual([1,0], p)

    def test_predict_cb_explore(self):

        vw = VowpalMediatorMock([0.25, 0.75])
        p = VowpalArgsLearner("--cb_explore 2", vw).predict(None, ['yes','no'])[0]

        self.assertIsInstance(vw._predict_calls[0], VowpalExampleMock)

        self.assertEqual({'x':None }, vw._predict_calls[0].ns)
        self.assertEqual(None       , vw._predict_calls[0].label)

        self.assertEqual([.25, .75], p)

    def test_predict_cb(self):

        vw = VowpalMediatorMock(2)
        p = VowpalArgsLearner("--cb 2", vw).predict(None, ['yes','no'])[0]

        self.assertEqual([0,1], p)

    def test_learn_cb_adf(self):
        
        vw = VowpalMediatorMock()
        learner = VowpalArgsLearner("--cb_explore_adf",vw)
        
        learner.predict(None, ['yes','no'])
        learner.learn(None, 'yes', 1, 0.2, ['yes','no'])

        self.assertEqual(2, len(vw._learn_calls[0]))

        self.assertEqual({'x':None }, vw._learn_calls[0][0].ns[0])
        self.assertEqual({'a':'yes'}, vw._learn_calls[0][0].ns[1])
        self.assertEqual("1:0:0.2"  , vw._learn_calls[0][0].label)

        self.assertEqual({'x':None }, vw._learn_calls[0][1].ns[0])
        self.assertEqual({'a':'no'} , vw._learn_calls[0][1].ns[1])
        self.assertEqual(None       , vw._learn_calls[0][1].label)

    def test_learn_cb(self):

        vw = VowpalMediatorMock()
        learner = VowpalArgsLearner("--cb_explore", vw)

        learner.predict(None, ['yes','no'])
        learner.learn(None, 'no', .5, 0.2, ['yes','no'])

        self.assertIsInstance(vw._learn_calls[0], VowpalExampleMock)

        self.assertEqual({'x':None}, vw._learn_calls[0].ns)
        self.assertEqual("2:0.5:0.2", vw._learn_calls[0].label)

    def test_flatten_tuples(self):

        vw = VowpalMediatorMock()
        learner = VowpalArgsLearner("--cb_explore", vw)

        learner.predict([(0,0,1)], ['yes','no'])
        learner.learn({'l':(0,0,1), 'j':1 }, 'no', .5, 0.2, ['yes','no'])

        self.assertIsInstance(vw._learn_calls[0], VowpalExampleMock)

        self.assertEqual({'x':[0,0,1]}, vw._predict_calls[0].ns)
        self.assertEqual(None, vw._predict_calls[0].label)

        self.assertEqual({'x':{'l_0':0, 'l_1':0, 'l_2':1, 'j':1}}, vw._learn_calls[0].ns)
        self.assertEqual("2:0.5:0.2", vw._learn_calls[0].label)


    def test_predict_epsilon_not_adf_args_error_1(self):
        learner = VowpalArgsLearner("--cb_explore --epsilon 0.75 --random_seed 20 --quiet")
        learner.predict(None, [1,2,3,4])

        with self.assertRaises(Exception) as e:
            learner.predict(None, [1,2,3,4,5])

        self.assertTrue("--cb_explore_adf" in str(e.exception))

    def test_predict_epsilon_not_adf_args_error_2(self):
        learner = VowpalArgsLearner("--cb_explore --epsilon 0.75 --random_seed 20 --quiet")
        learner.predict(None, [1,2,3,4])

        with self.assertRaises(Exception) as e:
            learner.predict(None, [1,2,3])

        self.assertTrue("--cb_explore_adf" in str(e.exception))

@unittest.skipUnless(importlib.util.find_spec("vowpalwabbit"), "VW is not installed")
class VowpalMediator_Tests(unittest.TestCase):

    def test_make_example_setup_done(self):
        from vowpalwabbit.pyvw import example

        vw = VowpalMediator()
        vw.init_learner("--cb_explore_adf --noconstant --quiet",4)
        ex = vw.make_example({'x':'a'}, None)

        self.assertTrue(hasattr(ex, "setup_done"))

    def test_make_example_single_string_value(self):

        from vowpalwabbit.pyvw import example

        vw = VowpalMediator()
        vw.init_learner("--cb_explore_adf --noconstant --quiet",4)
        ex = cast(example,vw.make_example({'x':'a'}, None))

        self.assertTrue(hasattr(ex, "setup_done"))
        self.assertEqual([(ex.get_feature_id("x","0=a"),1)],list(ex.iter_features()))

    def test_make_example_single_numeric_value(self):

        from vowpalwabbit.pyvw import example

        vw = VowpalMediator()
        vw.init_learner("--cb_explore_adf --noconstant --quiet",4)
        ex = cast(example,vw.make_example({'x':5}, None))

        self.assertEqual([(ex.get_feature_id("x",0),5)],list(ex.iter_features()))

    def test_make_example_dict_numeric_value(self):

        from vowpalwabbit.pyvw import example

        vw = VowpalMediator()
        vw.init_learner("--cb_explore_adf --noconstant --quiet",4)
        ex = cast(example,vw.make_example({'x':{'a':5}}, None))

        self.assertEqual([(ex.get_feature_id("x","a"),5)],list(ex.iter_features()))

    def test_make_example_dict_string_value(self):

        from vowpalwabbit.pyvw import example

        vw = VowpalMediator()
        vw.init_learner("--cb_explore_adf --noconstant --quiet",4)
        ex = cast(example,vw.make_example({'x':{'a':'b'}}, None))

        self.assertEqual([(ex.get_feature_id("x","a=b"),1)],list(ex.iter_features()))

    def test_make_example_list_numeric_value(self):

        from vowpalwabbit.pyvw import example

        vw = VowpalMediator()
        vw.init_learner("--cb_explore_adf --noconstant --quiet",4)
        ex = cast(example,vw.make_example({'x':[2]}, None))

        self.assertEqual([(ex.get_feature_id("x",0),2)],list(ex.iter_features()))

    def test_make_example_list_string_value(self):

        from vowpalwabbit.pyvw import example

        vw = VowpalMediator()
        vw.init_learner("--cb_explore_adf --noconstant --quiet",4)
        ex = cast(example,vw.make_example({'x':['a']}, None))

        self.assertEqual([(ex.get_feature_id("x","0=a"),1)],list(ex.iter_features()))

    def test_make_example_list_mixed_value(self):

        from vowpalwabbit.pyvw import example

        vw = VowpalMediator()
        vw.init_learner("--cb_explore_adf --noconstant --quiet",4)
        ex = cast(example,vw.make_example({'x':['a',3.2,'c']}, None))

        expected = [
            (ex.get_feature_id("x","0=a"),1),
            (ex.get_feature_id("x", 1),3.2),
            (ex.get_feature_id("x","2=c"),1)
        ]

        actual = list(ex.iter_features())

        self.assertEqual(expected[0],actual[0])
        self.assertEqual(expected[1],(actual[1][0],round(actual[1][1],4)))
        self.assertEqual(expected[2],actual[2])

    def test_make_example_label(self):

        from vowpalwabbit.pyvw import example, cbandits_label

        vw = VowpalMediator()
        vw.init_learner("--cb_explore 2 --noconstant --quiet",4)
        ex = cast(example,vw.make_example({'x':1}, "0:.5:1"))

        self.assertEqual(4, ex.labelType)
        self.assertEqual("0:0.5:1.0", str(cbandits_label(ex)))

    def test_make_examples_setup_done(self):
        vw = VowpalMediator()
        vw.init_learner("--cb_explore_adf --noconstant --quiet",4)
        exs = vw.make_examples({'x':1}, [{'a':2}, {'a':3}], None)

        for ex in exs:
            self.assertTrue(hasattr(ex, "setup_done"))

    def test_make_examples_namespaces(self):

        from vowpalwabbit.pyvw import example

        vw = VowpalMediator()
        vw.init_learner("--cb_explore_adf --noconstant --quiet",4)
        ex = cast(Sequence[example],vw.make_examples({'x':3}, [{'a':1},{'a':2}], None))

        self.assertEqual(2, len(ex))

        expected_0 = [
            (ex[0].get_feature_id("x",0),3),
            (ex[0].get_feature_id("a",1),1)
        ]

        expected_1 = [
            (ex[1].get_feature_id("x",0),3),
            (ex[1].get_feature_id("a",1),2)
        ]

        self.assertEqual(expected_0,list(ex[0].iter_features()))
        self.assertEqual(expected_1,list(ex[1].iter_features()))

    def test_make_examples_labels(self):
        from vowpalwabbit.pyvw import example, cbandits_label

        vw = VowpalMediator()
        vw.init_learner("--cb_explore_adf --noconstant --quiet", 4)
        exs = cast(Sequence[example],vw.make_examples({'x':1}, [{'a':1},{'a':2}], ["0:.5:1",""]))

        self.assertEqual(4, exs[0].labelType)
        self.assertEqual(4, exs[1].labelType)
        self.assertEqual("0:0.5:1.0", str(cbandits_label(exs[0])) )
        self.assertEqual("", str(cbandits_label(exs[1])) )

    def test_init_learner(self):
        vw = VowpalMediator()
        vw.init_learner("--cb_explore_adf --epsilon .1 --quiet", 4)
        self.assertIn("--cb_explore_adf", vw._vw.get_arguments())
        self.assertIn("--epsilon", vw._vw.get_arguments())

    def test_init_twice_exception(self):
        vw = VowpalMediator()
        vw.init_learner("--cb_explore_adf --epsilon .1 --quiet", 4)
        
        with self.assertRaises(CobaException) as ex:
            vw.init_learner("--cb_explore_adf --epsilon .1 --quiet", 4)
        
    def test_predict(self):

        vw = VowpalMediator()
        vw.init_learner("--cb_explore_adf --epsilon .1 --noconstant --quiet", 4)
        ex = vw.make_examples({}, [{'a':1}, {'a':2}], None)

        P = vw.predict(ex)

        self.assertEqual(2, len(P))

    def test_learn(self):

        vw = VowpalMediator()
        vw.init_learner("--cb_explore_adf --epsilon .1 --noconstant --quiet", 4)
        ex = vw.make_examples({}, [{'a':1}, {'a':2}], ["0:.5:1", ""])

        vw.learn(ex)

if __name__ == '__main__':
    unittest.main()