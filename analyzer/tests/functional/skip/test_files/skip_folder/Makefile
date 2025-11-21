OBJS = $(SRCS:.cpp=.o)

CXXFLAGS += -Wno-all -Wno-extra -Wno-division-by-zero

SRCS = skipme/skipme.cpp

all: $(OBJS)

.cpp.o:
	$(CXX) $(CXXFLAGS) -c $< -o $@

clean:
	rm -rf $(OBJS)
