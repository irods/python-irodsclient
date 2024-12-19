import irods

#  Used in test of:
#    irods.test.data_obj_test.TestDataObjOps.test_setting_xml_parser_choice_by_environment_only__issue_584
print(irods.client_configuration.connections.xml_parser_default)
