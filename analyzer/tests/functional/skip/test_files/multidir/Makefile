default: src/a.o src/b.o

src/b.o: src/b.cpp
	$(CXX) -c src/b.cpp -o /dev/null

src/a.o: src/a.cpp lib/lib.o
	$(CXX) -c src/a.cpp -o /dev/null

lib/lib.o: lib/lib.cpp
	$(CXX) -c lib/lib.cpp -o /dev/null

clean:
	rm -rf src/*.o lib/*.o
