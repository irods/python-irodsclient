TESTING NOTES
=============

| Test        | Status           | Notes |
| ------------- |-------------|------------|
| browse_test.py | fail  | `File "browse_test.py", line 12, in test_get_collection coll = sess.get_collection(path) AttributeError: 'iRODSSession' object has no attribute 'get_collection'`|
| coll_test.py | fail | requires username, password, host; fixable|
| file_test.py | fail |`File "file_test.py", line 9, in <module> obj = sess.get_data_object("/tempZone/home/rods/test1") AttributeError: 'iRODSSession' object has no attribute 'get_data_object'`|
| message_test.py | pass ||
| meta_test.py | fail | `
  File "meta_test.py", line 10, in <module>
    obj = sess.get_data_object("/tempZone/home/rods/test1")
AttributeError: 'iRODSSession' object has no attribute 'get_data_object'` |
| query_test.py | ||
| test_connection.py | ||

