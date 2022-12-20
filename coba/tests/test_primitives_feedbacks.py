import unittest

from coba.primitives import SequenceFeedback, BatchFeedback

class SequenceFeedback_Tests(unittest.TestCase):
    def test_sequence(self):
        fb = SequenceFeedback([4,5,6])

        self.assertEqual(3,len(fb))
        self.assertEqual([4,5,6],fb)
        self.assertEqual(4,fb[0])
        self.assertEqual(4,fb.eval(0))
        self.assertEqual(5,fb.eval(1))
        self.assertEqual(6,fb.eval(2))

class BatchFeedback_Tests(unittest.TestCase):

    def test_batch(self):

        batch = BatchFeedback([SequenceFeedback([4,5,6]),SequenceFeedback([7,8,9])])

        self.assertEqual(batch.eval([1,2]), [5,9])

if __name__ == '__main__':
    unittest.main()