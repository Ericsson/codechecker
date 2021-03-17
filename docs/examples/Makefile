project_root_dir := $(strip $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST)))))

runnable := $(project_root_dir)/ccexample

include_dir := $(project_root_dir)/incl 
object_dir := $(project_root_dir)/objs
source_dir := $(project_root_dir)/src
sources := $(wildcard $(source_dir)/*.c)
objects := $(patsubst $(source_dir)/%.c,$(object_dir)/%.c.o,$(sources))
depends := $(patsubst $(source_dir)/%.c,$(object_dir)/%.c.d,$(sources))

CFLAGS = -MMD -MP -g -std=c99 -Wall
CFLAGS += -I $(include_dir)

all: $(runnable)

$(runnable): $(objects)
	$(CC) $(LINKFLAGS) $^ -o $@

$(objects): $(object_dir)/%.c.o: $(source_dir)/%.c
	@mkdir --parents $(object_dir)
	$(CC) $(CFLAGS) $(CPPFLAGS) -c $< -o $@

.PHONY: clean
clean:
	rm --recursive --force $(object_dir)
	rm --force $(runnable)

ifneq ($(filter clean,$(MAKECMDGOALS)),clean)
-include $(depends)
endif