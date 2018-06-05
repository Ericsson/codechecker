
tidy1:
	clang-tidy -checks='-*,clang-diagnostic-*,clang-analyzer-*' test.cpp

tidy2:
	clang-tidy -checks='-*,clang-diagnostic-*,clang-analyzer-*' test2.cpp

tidy3:
	clang-tidy -checks='-*,clang-diagnostic-*,clang-analyzer-*,modernize-use-nullptr' test3.cpp -- -I.
