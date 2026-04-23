/*
 * LD_PRELOAD shim for a CS:APP-style bomb.
 *
 *  - gethostname()  returns $BOMB_USERID so initialize_bomb's strcasecmp
 *    against the baked-in userid passes.
 *  - gethostbyname() returns a hostent pointing at 127.0.0.1 so the socket
 *    connects to the fake grader on loopback, regardless of the name the
 *    bomb asked to resolve.
 *
 * Build:  make -C shim
 * Use:    LD_PRELOAD=./shim/libbombshim.so ./bomb
 *         (BOMB_USERID must be set. run.sh sources .env for you.)
 */

#define _GNU_SOURCE
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>
#include <netdb.h>
#include <arpa/inet.h>

int gethostname(char *name, size_t len) {
    const char *h = getenv("BOMB_USERID");
    if (!h || !*h) return -1;
    size_t n = strlen(h);
    if (len <= n) return -1;
    memcpy(name, h, n + 1);
    return 0;
}

static uint32_t       fake_addr = 0;
static char          *fake_addrs[2];
static char           fake_name[256];
static struct hostent fake_he;

struct hostent *gethostbyname(const char *name) {
    fake_addr = htonl(INADDR_LOOPBACK);
    fake_addrs[0] = (char *)&fake_addr;
    fake_addrs[1] = NULL;

    strncpy(fake_name, name ? name : "localhost", sizeof(fake_name) - 1);
    fake_name[sizeof(fake_name) - 1] = '\0';

    fake_he.h_name      = fake_name;
    fake_he.h_aliases   = NULL;
    fake_he.h_addrtype  = AF_INET;
    fake_he.h_length    = 4;
    fake_he.h_addr_list = fake_addrs;
    return &fake_he;
}
