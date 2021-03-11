#include "divide.hpp"

#include <iostream>
#include <stdlib.h>
#include <vector>

int main(int argc, char* argv[])
{
    std::cout << "CodeChecker example program." << '\n';

    std::vector<int> params;
    for (int i = 1; i < argc; ++i) {
        long value = strtol(argv[i], nullptr, 10);
        if (errno) {
            std::cerr << "Invalid parameter at position " << i << ".\n";
            return 1;
        } else {
            params.push_back(int(value));
        }
    }

    auto result = divide(params[0], params[1]);

    std::cout << "Division result is: " << result << ".\n";

    return 0;
}
