# Check if certain environmental variables are set properly.
include Makefile.check

# Execute the build of each API subfolder.
SUBDIRS := $(wildcard */.)

default: all

all: $(SUBDIRS)

$(SUBDIRS):
	VERSION=$(dir $@) $(MAKE) -C $@

.PHONY: all $(SUBDIRS)
