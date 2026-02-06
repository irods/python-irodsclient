import unittest
import irods
import irods.client_configuration as cfg

# Test assignments on the negative and positive space of the
# client configuration.

class TestClientConfigurationAttributes(unittest.TestCase):
    
    def test_hits_and_misses__issue_708(self):
        # For caching configuration objects
        configuration_level = {}

        #count=0; success=0
        for dotted_name, value, is_conf in cfg._var_items_as_generator():
            with self.subTest(dotted_name=dotted_name):
                name_parts=dotted_name.split('.')
                namespace='.'.join(name_parts[:-1])
                attribute_name=name_parts[-1]
                if isinstance(value, cfg.iRODSConfiguration):
                    configuration_level[dotted_name]=value
                else:
                    if is_conf:
                        #count += 1
                        try:
                            # Test the positive space, i.e. the 'hit'
                            setattr(configuration_level[namespace],attribute_name,value)

                            #print(namespace, attribute_name, value)

                            # Test the negative space, i.e. the 'miss'
                            with self.assertRaises(AttributeError):
                                setattr(configuration_level[namespace],attribute_name+'_1',value)
                        except Exception as exc:
                            self.fail(f"shouldn't fail but raised {exc = }")
                        else:
                            pass
                            #success += 1
        #print(f'{count = }/{success = }')
