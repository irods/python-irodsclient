
# https://github.com/irods/irods/blob/4.2.1/lib/core/include/irods_client_server_negotiation.hpp
# https://github.com/irods/irods/blob/4.2.1/lib/core/src/irods_client_negotiation.cpp

# Token sent to the server to request negotiation
REQUEST_NEGOTIATION = "request_server_negotiation"

# Negotiation request values
REQUIRE_SSL = "CS_NEG_REQUIRE"
REQUIRE_TCP = "CS_NEG_REFUSE"

# Negotiation result (response) values
FAILURE = "CS_NEG_FAILURE"
USE_SSL = "CS_NEG_USE_SSL"
USE_TCP = "CS_NEG_USE_TCP"

# Keywords
CS_NEG_SID_KW = "cs_neg_sid_kw"
CS_NEG_RESULT_KW = "cs_neg_result_kw"


def perform_negotiation(client_policy, server_policy):
    if REQUIRE_SSL in (client_policy, server_policy):
        if REQUIRE_TCP in (client_policy, server_policy):
            return FAILURE, 0
        return USE_SSL, 1
    return USE_TCP, 1


def validate_policy(policy):
    if policy not in (REQUIRE_SSL, REQUIRE_TCP):
        raise ValueError('Invalid client-server negotiation policy: {}'.format(policy))
