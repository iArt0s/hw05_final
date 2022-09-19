def compare_fields(obj, fields_to_test, test_object):
    for field in fields_to_test:
        field_name, expected_field_value, msg = field
        with obj.subTest():
            obj.assertEqual(
                getattr(test_object, field_name),
                expected_field_value,
                msg=msg
            )
