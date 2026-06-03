/*
To build, you need the PAM development library. Once installed,
run the following:

  gcc -fPIC -fno-stack-protector -o pam_clear_token.o -c main.c
  gcc -shared -o pam_clear_token.so pam_clear_token.o
*/

#include <security/pam_modules.h>
#include <security/pam_ext.h>
#include <security/pam_appl.h>

#include <stdlib.h>

PAM_EXTERN int pam_sm_authenticate(pam_handle_t* pamh, int flags, int argc, const char** argv)
{
    (void) flags;
    (void) argc;
    (void) argv;

    // Clear the current auth token.
    pam_set_item(pamh, PAM_AUTHTOK, NULL);
    pam_set_item(pamh, PAM_OLDAUTHTOK, NULL);

    return PAM_SUCCESS;
}

PAM_EXTERN int pam_sm_setcred(pam_handle_t* pamh, int flags, int argc, const char** argv)
{
    (void) pamh;
    (void) flags;
    (void) argc;
    (void) argv;

    return PAM_SUCCESS;
}
