
tidy1:
	clang-tidy -checks='-*,clang-diagnostic-*,clang-analyzer-*' test.cpp

tidy2:
	clang-tidy -checks='-*,clang-diagnostic-*,clang-analyzer-*' test2.cpp

tidy3:
	clang-tidy -checks='-*,clang-diagnostic-*,clang-analyzer-*,modernize-use-nullptr' test3.cpp -- -I.

tidy4:
	clang-tidy -checks='-*,clang-diagnostic-*,clang-analyzer-*' test4.cpp -- -Wc++11-compat-reserved-user-defined-literal
