CC = gcc
CFLAGS = -O2 -Wall -fPIC
LDFLAGS = -shared

libbombshim.so: shim.c
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $<

clean:
	rm -f libbombshim.so

.PHONY: clean
