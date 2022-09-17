def compare_fields(self, fields_to_test, test_object):
    for field in fields_to_test:
        field_name, expected_field_value, msg = field
        with self.subTest():
            self.assertEqual(
                getattr(test_object, field_name),
                expected_field_value,
                msg=msg
            )