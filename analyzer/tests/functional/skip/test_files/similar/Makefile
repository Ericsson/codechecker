OBJS = $(SRCS:.cpp=.o)

CXXFLAGS = -Wno-all -Wno-extra -Wno-division-by-zero

SRCS = simple.c \
		simple.cc

.cpp.o:
	$(CXX) $(CXXFLAGS) -c $<  -o $@

all: $(OBJS)

clean:
	rm -rf *.o
