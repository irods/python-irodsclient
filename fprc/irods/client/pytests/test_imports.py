from os.path import abspath, dirname, join
import sys

verbose = False

def do_imports():
    import irods.client
    import irods.client.utility.password_obfuscation
    import irods.client.low_level.message.property_types
    import irods.client.low_level.client_server_negotiation
    import irods.client.low_level.message.ordered
    import irods.client.low_level.message.property_types
    import irods.client.low_level.message.quasixml
    import irods.client.low_level.message.message
    import irods.client.low_level.keywords
    import irods.client.low_level.exception

    return irods.client.low_level.message.ET()

def test_et():
  assert do_imports() is not None

if __name__ == '__main__':
    verbose = True
    print(do_imports())
