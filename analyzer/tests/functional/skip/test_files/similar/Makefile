C_OBJS = $(C_SRCS:.c=_c.o)
CPP_OBJS = $(CPP_SRCS:.cpp=_cpp.o)

OBJS =  $(C_OBJS) $(CPP_OBJS)

CXXFLAGS = -Wno-all -Wno-extra -Wno-division-by-zero

C_SRCS = simple.c
CPP_SRCS = simple.cpp

all: $(C_OBJS) $(CPP_OBJS)

$(CPP_OBJS): %_cpp.o: %.cpp
	$(CXX) $(CXXFLAGS) -c $<  -o $@

$(C_OBJS): %_c.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -rf $(OBJS)
