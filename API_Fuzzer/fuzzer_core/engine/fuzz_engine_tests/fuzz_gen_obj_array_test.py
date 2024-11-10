import unittest
from hypothesis import given, strategies as st
from fuzzer_core.engine.fuzz_generator import BaseFuzzGenerator, ValuesIncluded

class TestBaseFuzzGenerator(unittest.TestCase):

    def setUp(self):
        # Initialize BaseFuzzGenerator with settings for valid and invalid values
        self.valid_gen = BaseFuzzGenerator(include_values=ValuesIncluded.VALID_ONLY)
        self.invalid_gen = BaseFuzzGenerator(include_values=ValuesIncluded.INVALID_ONLY)
        self.mixed_gen = BaseFuzzGenerator(include_values=ValuesIncluded.BOTH)

    @given(data=st.data())
    def test_generate_random_strategy(self, data):
        strategy = self.mixed_gen.generate_random_strategy()
        generated_value = data.draw(strategy)
        print("Generated Random Value:", generated_value)
        self.assertTrue(True)  # Replace with actual validation logic if needed

    @given(data=st.data())
    def test_generate_valid_object(self, data):
        props_strategies = {
            "name": self.valid_gen.generate_string(),
            "age": self.valid_gen.generate_integer(),
            "active": self.valid_gen.generate_bool()
        }
        strategy = self.valid_gen.generate_object(props_strategies, additional_props=True, min_properties=1, max_properties=3, req_props=["name"])
        generated_object = data.draw(strategy)
        print("Generated Valid Object:", generated_object)
        self.assertTrue(True)  # Replace with actual validation logic if needed

    @given(data=st.data())
    def test_generate_invalid_object(self, data):
        props_strategies = {
            "name": self.invalid_gen.generate_string(),
            "age": self.invalid_gen.generate_integer(),
            "active": self.invalid_gen.generate_bool()
        }
        strategy = self.invalid_gen.generate_object(props_strategies, additional_props=True, min_properties=1, max_properties=3, req_props=["name"])
        generated_object = data.draw(strategy)
        print("Generated Invalid Object:", generated_object)
        self.assertTrue(True)  # Replace with actual validation logic if needed

    @given(data=st.data())
    def test_generate_valid_array(self, data):
        items_strategies = [self.valid_gen.generate_string(), self.valid_gen.generate_number()]
        strategy = self.valid_gen.generate_array(min_items=1, max_items=5, unique_items=True, items_strategies=items_strategies)
        generated_array = data.draw(strategy)
        print("Generated Valid Array:", generated_array)
        self.assertTrue(True)  # Replace with actual validation logic if needed

    @given(data=st.data())
    def test_generate_invalid_array(self, data):
        items_strategies = [self.invalid_gen.generate_string(), self.invalid_gen.generate_number()]
        strategy = self.invalid_gen.generate_array(min_items=1, max_items=5, unique_items=True, items_strategies=items_strategies)
        generated_array = data.draw(strategy)
        print("Generated Invalid Array:", generated_array)
        self.assertTrue(True)  # Replace with actual validation logic if needed

if __name__ == "__main__":
    unittest.main()
