#include "ArgParser.hpp"

#include <boost/program_options/variables_map.hpp>

#include <ctype.h>
#include <iostream>
#include <memory>

namespace {

int convertCompressionLevel(char level)
{
    if (isdigit(level)) {
        return (int(level) - int('0'));
    } else {
        switch (level) {
            case 'n':
            case 'N':
                return 0;
            case 'l':
            case 'L':
                return 2;
            case 'm':
            case 'M':
                return 5;
            case 'h':
            case 'H':
                return 9;
            default:
                return -1;
        }
    }
}

}

int main(int argc, char* argv[])
{
    std::cout << "CodeChecker example program." << '\n';
    std::unique_ptr<boost::program_options::variables_map> programOptionMap =
        parseArguments(argc, argv);
    if (programOptionMap == nullptr) {
        return 0;
    }

    int compressionLevel;
    compressionLevel = convertCompressionLevel(
        (*programOptionMap)["compression"].as<char>());
    if (compressionLevel < 0) {
        std::cerr << "Invalid compression level was set." << '\n';
        return 1;
    }

    std::cout << "Compression level was set to " << compressionLevel << ".\n";

    return 0;
}
