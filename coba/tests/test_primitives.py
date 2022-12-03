import unittest

from coba.primitives import Categorical, Sparse, Dense, HashableSparse, HashableDense

class DummySparse(Sparse):

    def __init__(self, row) -> None:
        self._row = row

    def __getitem__(self, key):
        ...

    def __len__(self) -> int:
        ...

    def __iter__(self):
        ...

    def keys(self):
        ...

    def items(self):
        return self._row.items()

class DummyDense(Dense):

    def __init__(self, row) -> None:
        self._row = row

    def __getitem__(self, key):
        ...

    def __len__(self) -> int:
        return len(self._row)

    def __iter__(self):
        return iter(self._row)

class Dense_Tests(unittest.TestCase):

    def test_getattr(self):

        class DummyClass:
            def __init__(self) -> None:
                self.missing = True

        self.assertEqual(True, DummyDense(DummyClass()).missing)

        with self.assertRaises(AttributeError):
            self.assertEqual(True, DummyDense({'a':1}).missing)

    def test_eq(self):

        self.assertEqual(DummyDense([1,2,3]),[1,2,3])

    def test_bad_eq(self):

        self.assertNotEqual(DummyDense([1,2,3]),1)

class Sparse_Tests(unittest.TestCase):

    def test_simple(self):

        class DummyClass:
            def __init__(self) -> None:
                self.missing = True

        self.assertEqual(True, DummySparse(DummyClass()).missing)

        with self.assertRaises(AttributeError):
            self.assertEqual(True, DummySparse({'a':1}).missing)

    def test_eq(self):

        self.assertEqual(DummySparse({'a':1}),{'a':1})

    def test_bad_eq(self):

        self.assertNotEqual(DummySparse({'a':1}),1)

class Categorical_Tests(unittest.TestCase):
    def test_value(self):
        self.assertEqual("A", Categorical("A",["A","B"]))
    
    def test_levels(self):
        self.assertEqual(["A","B"], Categorical("A",["A","B"]).levels)

    def test_eq(self):
        self.assertEqual(Categorical("A",["A","B"]), Categorical("A",["A","B"]))

    def test_ne(self):
        self.assertNotEqual(1, Categorical("A",["A","B"]))

    def test_str(self):
        self.assertEqual("A", str(Categorical("A",["A","B"])))

    def test_repr(self):
        self.assertEqual("Categorical('A',['A', 'B'])", repr(Categorical("A",["A","B"])))

class HashableSparse_Tests(unittest.TestCase):

    def test_get(self):
        hash_dict = HashableSparse({'a':1,'b':2})
        self.assertEqual(1,hash_dict['a'])

    def test_len(self):
        hash_dict = HashableSparse({'a':1,'b':2})
        self.assertEqual(2,len(hash_dict))

    def test_iter(self):
        hash_dict = HashableSparse({'a':1,'b':2})
        self.assertEqual(['a','b'],list(hash_dict))

    def test_len(self):
        hash_dict = HashableSparse({'a':1,'b':2})
        self.assertEqual(2,len(hash_dict))

    def test_hash(self):
        hash_dict = HashableSparse({'a':1,'b':2})
        self.assertEqual(hash(hash_dict), hash(hash_dict))
        self.assertEqual(hash_dict,hash_dict)

    def test_eq(self):
        hash_dict = HashableSparse({'a':1,'b':2})
        self.assertEqual({'a':1,'b':2},hash_dict)

    def test_repr(self):
        hash_dict = HashableSparse({'a':1,'b':2})
        self.assertEqual("{'a': 1, 'b': 2}",repr(hash_dict))
    
    def test_str(self):
        hash_dict = HashableSparse({'a':1,'b':2})
        self.assertEqual("{'a': 1, 'b': 2}",str(hash_dict))

class HashableDense_Tests(unittest.TestCase):

    def test_get(self):
        hash_seq = HashableDense([1,2,3])
        self.assertEqual(2,hash_seq[1])

    def test_len(self):
        hash_seq = HashableDense([1,2,3])
        self.assertEqual(3,len(hash_seq))

    def test_hash(self):
        hash_seq = HashableDense([1,2,3])
        self.assertEqual(hash(hash_seq), hash(hash_seq))
        self.assertEqual(hash_seq,hash_seq)

    def test_eq(self):
        hash_seq = HashableDense([1,2,3])
        self.assertEqual([1,2,3],hash_seq)
        self.assertEqual((1,2,3),hash_seq)

    def test_neq(self):
        hash_seq = HashableDense([1,2,3])
        self.assertNotEqual([1,2,4],hash_seq)
        self.assertNotEqual([1,2,3,4],hash_seq)
        self.assertNotEqual(1,hash_seq)
    
    def test_repr(self):
        hash_seq = HashableDense([1,2,3])
        self.assertEqual("[1, 2, 3]",repr(hash_seq))
    
    def test_str(self):
        hash_seq = HashableDense([1,2,3])
        self.assertEqual("[1, 2, 3]",str(hash_seq))

if __name__ == '__main__':
    unittest.main()
