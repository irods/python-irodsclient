import irods.session
#s = h.make_session()
s = irods.session.iRODSSession(
  port=1247,
  host='localhost',
  zone='tempZone',
  user='alice'
  ,password='test123'
)
c = s.collections.get('/tempZone/home/public')
import pprint
print('user is {}'.format( s.username))
print(c)
