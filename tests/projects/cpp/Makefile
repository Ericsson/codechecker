all:
	$(CXX) -c call_and_message.cpp -Wno-all -Wno-extra
	$(CXX) -c divide_zero.cpp -Wno-all -Wno-extra -Wno-division-by-zero
	$(CXX) -c divide_zero_duplicate.cpp -Wno-all -Wno-extra
	$(CXX) -c file_to_be_skipped.cpp -Wno-all -Wno-extra
	$(CXX) -c has\ a\ space.cpp -Wno-all -Wno-extra
	$(CXX) -c new_delete.cpp -Wno-all -Wno-extra
	$(CXX) -c null_dereference.cpp -Wno-all -Wno-extra
	$(CXX) -c stack_address_escape.cpp -Wno-all -Wno-extra
	$(CXX) -c skip_header.cpp -Wno-all -Wno-extra -Wno-division-by-zero
	$(CXX) -c path_begin1.cpp -Wno-all -Wno-extra
	$(CXX) -c path_begin2.cpp -Wno-all -Wno-extra
	$(CXX) -c -DVAR=2 path_begin.cpp -Wno-all -Wno-extra
	$(CXX) -c -DVAR=1 path_begin.cpp -Wno-all -Wno-extra
	$(CC) -c statistical_checkers.c -Wno-all -Wno-extra
clean:
	rm -f call_and_message.o
	rm -f divide_zero.o
	rm -f divide_zero_duplicate.o
	rm -f file_to_be_skipped.o
	rm -f has\ a\ space.o
	rm -f new_delete.o
	rm -f null_dereference.o
	rm -f stack_address_escape.o
	rm -f skip_header.o
	rm -f path_begin1.o
	rm -f path_begin2.o
	rm -f path_begin.o
	rm -f statistical_checkers.o
