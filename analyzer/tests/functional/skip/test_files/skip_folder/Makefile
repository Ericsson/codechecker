OBJS = $(SRCS:.cpp=.o)

CXXFLAGS = -Wno-all -Wno-extra -Wno-division-by-zero

SRCS = skipme/skipme.cpp

.cpp.o:
	$(CXX) $(CXXFLAGS) -c $<  -o $@

all: $(OBJS)

clean:
	rm -rf skipme/*.o
