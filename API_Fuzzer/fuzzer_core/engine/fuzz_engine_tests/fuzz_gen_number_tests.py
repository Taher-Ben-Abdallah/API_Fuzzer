import unittest
from hypothesis import given
from hypothesis import strategies as st
from fuzzer_core.engine.fuzz_generator import BaseFuzzGenerator, ValuesIncluded

class TestBaseFuzzGenerator(unittest.TestCase):
    def setUp(self):
        self.valid_gen = BaseFuzzGenerator(include_values=ValuesIncluded.VALID_ONLY)
        self.invalid_gen = BaseFuzzGenerator(include_values=ValuesIncluded.INVALID_ONLY)
        self.both_gen = BaseFuzzGenerator(include_values=ValuesIncluded.BOTH)

    @given(st.integers(min_value=10, max_value=20).filter(lambda x: x % 2 == 0))
    def test_generate_integer_valid(self, value):
        print(f"Valid Integer: {value}")
        self.assertTrue(10 <= value <= 20)
        self.assertEqual(value % 2, 0)

    @given(st.integers().filter(lambda x: x < 10 or x > 20 or x % 2 != 0))
    def test_generate_integer_invalid(self, value):
        print(f"Invalid Integer: {value}")
        self.assertTrue(value < 10 or value > 20 or value % 2 != 0)

    @given(st.integers(min_value=-1000, max_value=1000).filter(lambda x: x % 5 == 0))
    def test_generate_int32_valid(self, value):
        print(f"Valid Int32: {value}")
        self.assertTrue(-1000 <= value <= 1000)
        self.assertEqual(value % 5, 0)

    @given(st.integers().filter(lambda x: x < -1000 or x > 1000 or x % 5 != 0))
    def test_generate_int32_invalid(self, value):
        print(f"Invalid Int32: {value}")
        self.assertTrue(value < -1000 or value > 1000 or value % 5 != 0)

    @given(st.integers(min_value=-1000000, max_value=1000000).filter(lambda x: x % 10 == 0))
    def test_generate_int64_valid(self, value):
        print(f"Valid Int64: {value}")
        self.assertTrue(-1000000 <= value <= 1000000)
        self.assertEqual(value % 10, 0)

    @given(st.integers().filter(lambda x: x < -1000000 or x > 1000000 or x % 10 != 0))
    def test_generate_int64_invalid(self, value):
        print(f"Invalid Int64: {value}")
        self.assertTrue(value < -1000000 or value > 1000000 or value % 10 != 0)

    @given(st.floats(min_value=1.5, max_value=9.5).filter(lambda x: abs(x % 0.5) <= 0.00001))
    def test_generate_float_valid(self, value):
        print(f"Valid Float: {value}")
        self.assertTrue(1.5 <= value <= 9.5)
        self.assertAlmostEqual(value % 0.5, 0, delta=0.00001)

    @given(st.floats().filter(lambda x: x < 1.5 or x > 9.5 or abs(x % 0.5) > 0.00001))
    def test_generate_float_invalid(self, value):
        print(f"Invalid Float: {value}")
        self.assertTrue(value < 1.5 or value > 9.5 or abs(value % 0.5) > 0.00001)

    @given(st.one_of(st.integers(min_value=-50, max_value=50).filter(lambda x: x % 7 == 0),
                     st.floats(min_value=-50, max_value=50).filter(lambda x: x % 7 == 0)))
    def test_generate_number_valid(self, value):
        print(f"Valid Number: {value}")
        self.assertTrue(-50 <= value <= 50)
        self.assertEqual(value % 7, 0)

    @given(st.one_of(st.integers().filter(lambda x: x < -50 or x > 50 or x % 7 != 0),
                     st.floats().filter(lambda x: x < -50 or x > 50 or x % 7 != 0)))
    def test_generate_number_invalid(self, value):
        print(f"Invalid Number: {value}")
        self.assertTrue(value < -50 or value > 50 or value % 7 != 0)

if __name__ == "__main__":
    unittest.main()
