import unittest

from o2a import O68Preprocessor


class IdentifierTests(unittest.TestCase):
    def setUp(self):
        self.preprocessor = O68Preprocessor()

    def test_algol68_separators_are_ignored(self):
        self.assertEqual(self.preprocessor.normalize_identifier("my_shape"), "myshape")
        self.assertEqual(self.preprocessor.normalize_identifier("my shape"), "myshape")
        self.assertEqual(self.preprocessor.normalize_identifier("My_Shape"), "myshape")

    def test_invalid_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            self.preprocessor.normalize_identifier("my-shape")

    def test_identifiers_with_separators_parse(self):
        source = """
        CLASS shape_class =
        BEGIN
            INT x_coordinate
            METHOD get_x_coordinate: INT: (x_coordinate)
        END
        """
        self.preprocessor.parse_o68(source)
        self.assertIn("shapeclass", self.preprocessor.classes)
        shape = self.preprocessor.classes["shapeclass"]
        self.assertEqual(shape["fields"][0]["name"], "xcoordinate")
        self.assertEqual(shape["methods"][0]["name"], "getxcoordinate")

    def test_semicolon_is_optional_at_end_of_sequence(self):
        source = "CLASS shape = BEGIN INT x; METHOD name: STRING: (\"ok\") END"
        self.preprocessor.parse_o68(source)
        self.assertEqual(self.preprocessor.classes["shape"]["fields"][0]["name"], "x")
        self.assertEqual(self.preprocessor.classes["shape"]["methods"][0]["name"], "name")

    def test_hash_in_string_is_not_a_comment(self):
        source = 'CLASS shape = BEGIN METHOD name: STRING: ("#") END'
        self.preprocessor.parse_o68(source)
        self.assertEqual(self.preprocessor.classes["shape"]["methods"][0]["body"], '"#"')


if __name__ == "__main__":
    unittest.main()
