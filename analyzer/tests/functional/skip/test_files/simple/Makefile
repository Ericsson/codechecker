OBJS = $(SRCS:.cpp=.o)

CXXFLAGS = -Wno-all -Wno-extra -Wno-division-by-zero

SRCS = skip_header.cpp \
		file_to_be_skipped.cpp

.cpp.o:
	$(CXX) $(CXXFLAGS) -c $<  -o $@

all: $(OBJS)

clean:
	rm -rf *.o
