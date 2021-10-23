import unittest
import timeit

from coba.utilities import HashableDict
from coba.simulations import Interaction
from coba.encodings import NumericEncoder, OneHotEncoder, InteractionTermsEncoder

class Performance_Tests(unittest.TestCase):
    
    def test_numeric_encode_performance_small(self):

        encoder   = NumericEncoder()
        many_ones = ["1"]*100
        
        time = min(timeit.repeat(lambda:encoder.encode(many_ones), repeat=1000, number=4))
        
        #was approximately .000122
        self.assertLess(time, .0002)

    def test_numeric_encode_performance_large(self):

        encoder   = NumericEncoder()
        many_ones = ["1"]*100000
        
        time = min(timeit.repeat(lambda:encoder.encode(many_ones), repeat=100, number=1))
        
        #was approximately .0301
        self.assertLess(time, .05)

    def test_onehot_fit_performance(self):

        fit_values = list(range(1000))

        time = min(timeit.repeat(lambda:OneHotEncoder(fit_values), repeat=100, number = 1))

        #was approximately 0.017
        self.assertLess(time, .03)

    def test_onehot_encode_performance(self):

        encoder = OneHotEncoder(list(range(1000)), error_if_unknown=False )
        to_encode = [100,200,300,400,-1]*100000

        time = min(timeit.repeat(lambda:encoder.encode(to_encode), repeat=50, number = 1))

        #was approximately 0.040
        self.assertLess(time, 1)

    def test_interaction_encode_performance(self):
        encoder = InteractionTermsEncoder(["xxa"])

        x = dict(zip(map(str,range(100)), range(100)))
        a = [1,2,3]
        
        time = timeit.timeit(lambda: encoder.encode(x=x, a=a), number=100)
        
        #print(time)
        #best observed was 0.62 without interning
        #best observed was 0.87 with interning
        #performance time could be reduced to around .47 by using numpy and prime factorization of feature names 
        self.assertLess(time, 1.0)

    def test_interaction_context_performance(self):

        interaction = Interaction([1,2,3]*100, (1,2,3), rewards=(4,5,6))

        time = timeit.timeit(lambda: interaction.context, number=10000)

        #old best was 0.6 on my machine
        self.assertLess(time, 1.5)

    def test_hashable_dict_performance(self):

        base_dict = dict(enumerate(range(1000)))

        time1 = timeit.timeit(lambda: dict(enumerate(range(1000))), number=1000)
        time2 = timeit.timeit(lambda: HashableDict(base_dict)     , number=1000)

        self.assertLess(abs(time1-time2), 1)

if __name__ == '__main__':
    unittest.main()