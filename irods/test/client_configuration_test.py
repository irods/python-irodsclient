import unittest

import irods.client_configuration as cfg


# Test assignments on the negative and positive space of the
# client configuration.
class TestClientConfigurationAttributes(unittest.TestCase):
    def test_configuration_writes_and_miswrites__issue_708(self):
        # For caching configuration objects
        configuration_level = {}
        leaf_names = []

        for dotted_name, value, is_conf in cfg._var_items_as_generator():  # noqa: SLF001
            with self.subTest(dotted_name=dotted_name):
                name_parts = dotted_name.split('.')
                namespace = '.'.join(name_parts[:-1])
                attribute_name = name_parts[-1]
                if isinstance(value, cfg.iRODSConfiguration):
                    # Store a parent object corresponding to a namespace.  For any leaf value
                    # subsequently found in the top-down descent, to be sitting directly within
                    # that namespace, the "else is_conf" part of this if/else will run the core
                    # part of the test on the corresponding configuration setting.
                    configuration_level[dotted_name] = value
                elif is_conf:
                    # A configuration setting was actually found (i.e. a "leaf" value within a dotted name.)

                    # Store the leaf name for proof positive of subtests actually run.
                    leaf_names.append(attribute_name)

                    # Test the positive space, i.e. the 'hit'.  This simply tests that the
                    # setting may be written to without error:
                    setattr(configuration_level[namespace], attribute_name, value)

                    # Test the negative space, i.e. a deliberate 'miss'.  This time we must fail;
                    # otherwise we'd get a silent miswrite in the form of a write to the incorrect attribute.
                    # (The new __slots__ members are there to prevent this):
                    with self.assertRaises(AttributeError):
                        setattr(configuration_level[namespace], attribute_name + '_1', value)

        # These cases were identified as likely ones for possible failed writes via misspelling.
        self.assertIn('irods_query_limit', leaf_names)
        self.assertIn('xml_parser_default', leaf_names)
