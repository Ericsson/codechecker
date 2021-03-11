project_root_dir := $(strip $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST)))))

runnable := $(project_root_dir)/ccexample

include_dir := $(project_root_dir)/incl 
object_dir := $(project_root_dir)/objs
source_dir := $(project_root_dir)/src
sources := $(wildcard $(source_dir)/*.cpp)
objects := $(patsubst $(source_dir)/%.cpp,$(object_dir)/%.cpp.o,$(sources))
depends := $(patsubst $(source_dir)/%.cpp,$(object_dir)/%.cpp.d,$(sources))

CXXFLAGS = -MMD -MP -g -std=c++17 -Wall -Wno-c++98-compat -Werror
CXXFLAGS += -I $(include_dir)

all: $(runnable)

$(runnable): $(objects)
	$(CXX) $(LINKFLAGS) $^ -o $@

$(objects): $(object_dir)/%.cpp.o: $(source_dir)/%.cpp
	@mkdir --parents $(object_dir)
	$(CXX) $(CXXFLAGS) $(CPPFLAGS) -c $< -o $@

.PHONY: clean
clean:
	rm --recursive --force $(object_dir)
	rm --force $(runnable)

ifneq ($(filter clean,$(MAKECMDGOALS)),clean)
-include $(depends)
endif