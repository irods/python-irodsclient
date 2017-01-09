
IRODS_SERVER_HOST = "rodserver"
IRODS_SERVER_PORT = "1247"
IRODS_SERVER_ZONE = "tempZone"
IRODS_SERVER_DN = \
    '/O=Grid/OU=GlobusTest/OU=simpleCA-45d266dde38f/CN=host/rodserver'
IRODS_USER_USERNAME = "rodsminer"
IRODS_USER_PASSWORD = "icatserver"
IRODS_AUTHENTICATION_SCHEME = "GSI"
IRODS_SERVER_VERSION = (4, 1, 10)

# # TO BE EXECUTED before running tests:
# export X509_CERT_DIR="/opt/certificates/caauth"
# export X509_USER_CERT="/opt/certificates/rodsminer/userkey.pem"
# export X509_USER_KEY="/opt/certificates/rodsminer/usercert.pem"
