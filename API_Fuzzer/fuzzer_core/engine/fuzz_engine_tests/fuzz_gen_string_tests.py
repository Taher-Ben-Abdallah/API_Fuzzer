import unittest
import re
from hypothesis import given, settings, strategies as st
from fuzzer_core.engine.fuzz_generator import BaseFuzzGenerator, ValuesIncluded

class TestBaseFuzzGeneratorStrings(unittest.TestCase):
    def setUp(self):
        self.valid_gen = BaseFuzzGenerator(include_values=ValuesIncluded.VALID_ONLY)
        self.invalid_gen = BaseFuzzGenerator(include_values=ValuesIncluded.INVALID_ONLY)
        self.both_gen = BaseFuzzGenerator(include_values=ValuesIncluded.BOTH)

    @settings(max_examples=10)
    @given(st.integers(min_value=5, max_value=10))
    def test_generate_string_valid(self, length):
        strategy = self.valid_gen.generate_string(min_length=length, max_length=length + 5, pattern=r'^[a-zA-Z]+$')
        for _ in range(10):
            value = strategy.example()
            print(f"Valid String: {value}")
            self.assertTrue(length <= len(value) <= length + 5)
            self.assertRegex(value, r'^[a-zA-Z]+$')

    @settings(max_examples=10)
    @given(st.integers(min_value=5, max_value=10))
    def test_generate_string_invalid(self, length):
        strategy = self.invalid_gen.generate_string(min_length=length, max_length=length + 5, pattern=r'^[a-zA-Z]+$')
        for _ in range(10):
            value = strategy.example()
            print(f"Invalid String: {value}")
            self.assertTrue(len(value) < length or len(value) > length + 5 or not re.match(r'^[a-zA-Z]+$', value))

    @settings(max_examples=10)
    def test_generate_string_with_enum_valid(self):
        enum = ["apple", "banana", "cherry"]
        strategy = self.valid_gen.generate_string(enum=enum)
        for _ in range(10):
            value = strategy.example()
            print(f"Valid String from Enum: {value}")
            self.assertIn(value, enum)

    @settings(max_examples=10)
    def test_generate_string_with_enum_invalid(self):
        enum = ["apple", "banana", "cherry"]
        strategy = self.invalid_gen.generate_string(enum=enum)
        for _ in range(10):
            value = strategy.example()
            print(f"Invalid String (not in Enum): {value}")
            self.assertNotIn(value, enum)

    @settings(max_examples=10)
    def test_generate_string_with_format_valid(self):
        strategy = self.valid_gen.generate_string(string_format="email")
        for _ in range(10):
            value = strategy.example()
            print(f"Valid Email String: {value}")
            self.assertRegex(value, r'^[^@]+@[^@]+\.[^@]+$')

    @settings(max_examples=10)
    def test_generate_string_with_format_invalid(self):
        strategy = self.invalid_gen.generate_string(string_format="email")
        for _ in range(10):
            value = strategy.example()
            print(f"Invalid Email String: {value}")
            self.assertNotRegex(value, r'^[^@]+@[^@]+\.[^@]+$')

    @settings(max_examples=10)
    def test_generate_string_with_length_and_format_valid(self):
        strategy = self.valid_gen.generate_string(min_length=8, max_length=15, string_format="uuid")
        for _ in range(10):
            value = strategy.example()
            print(f"Valid UUID String: {value}")
            self.assertRegex(value, r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')

    @settings(max_examples=10)
    def test_generate_string_with_length_and_format_invalid(self):
        strategy = self.invalid_gen.generate_string(min_length=8, max_length=15, string_format="uuid")
        for _ in range(10):
            value = strategy.example()
            print(f"Invalid UUID String: {value}")
            self.assertNotRegex(value, r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')

    @settings(max_examples=20)
    def test_generate_string_both_valid_and_invalid(self):
        strategy = self.both_gen.generate_string(min_length=5, max_length=10, pattern=r'^[a-zA-Z]+$')
        for _ in range(20):
            value = strategy.example()
            print(f"String: {value}")

if __name__ == '__main__':
    unittest.main()
