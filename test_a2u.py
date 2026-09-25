import unittest

from a2u import convert


class A2UTests(unittest.TestCase):
    def test_uppercase_words_become_math_bold(self):
        result = convert("MODE SHAPE = STRUCT(INT X);")
        self.assertIn("𝖬𝖮𝖣𝖤", result)
        self.assertIn("𝖲𝖧𝖠𝖯𝖤", result)
        self.assertIn("𝖨𝖭𝖳", result)
        self.assertIn("𝖷", result)

    def test_lowercase_identifiers_become_math_italic(self):
        result = convert("shape := circle; socket_listen := 1;")
        self.assertIn("𝑠ℎ𝑎𝑝𝑒", result)
        self.assertIn("𝑐𝑖𝑟𝑐𝑙𝑒", result)
        self.assertIn("𝑠𝑜𝑐𝑘𝑒𝑡_𝑙𝑖𝑠𝑡𝑒𝑛", result)

    def test_digits_and_punctuation_are_preserved(self):
        source = "X := foo_bar(10, 20) /= 0;"
        result = convert(source)
        self.assertIn("𝖷 := 𝑓𝑜𝑜_𝑏𝑎𝑟(10, 20) /= 0;", result)

    def test_comments_and_strings_are_unchanged(self):
        source = '# MODE foo\nprint("MODE foo", foo)'
        result = convert(source)
        self.assertEqual(result, '# MODE foo\n𝑝𝑟𝑖𝑛𝑡("MODE foo", 𝑓𝑜𝑜)')

    def test_mixed_case_extensions_are_unchanged(self):
        self.assertEqual(convert("CamelCase"), "CamelCase")


if __name__ == "__main__":
    unittest.main()
