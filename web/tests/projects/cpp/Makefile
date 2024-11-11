OBJS = $(SRCS:.cpp=.o)

CXXFLAGS = -Wno-all -Wno-extra -std=c++11

SRCS = call_and_message.cpp \
	   divide_zero.cpp \
	   divide_zero_duplicate.cpp \
	   file_to_be_skipped.cpp \
	   new_delete.cpp \
	   null_dereference.cpp \
	   stack_address_escape.cpp \
	   skip_header.cpp \
	   path_begin1.cpp \
	   path_begin2.cpp \
	   statistical_checkers.cpp

.cpp.o:
	$(CXX) $(CXXFLAGS) -c $<  -o $@

all: $(OBJS) space path_begin_var1 path_begin_var2

space:
	$(CXX) -c has\ a\ space.cpp -Wno-all -Wno-extra

path_begin_var1:
	$(CXX) -c -DVAR=1 path_begin.cpp -Wno-all -Wno-extra

path_begin_var2:
	$(CXX) -c -DVAR=2 path_begin.cpp -Wno-all -Wno-extra

clean:
	rm -rf *.o
