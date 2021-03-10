#include "ArgParser.hpp"

#include <boost/program_options.hpp>
#include <boost/program_options/variables_map.hpp>

#include <iostream>
#include <memory>

namespace {

std::unique_ptr<boost::program_options::options_description>
describeArguments()
{
    auto optionDescriptor =
        std::make_unique<boost::program_options::options_description>(
            "Options for ccexample program");
    optionDescriptor->add_options()
        ("help", "CodeChecker example program.")
        ("compression",
            boost::program_options::value<char>()->default_value('9'),
            "Set compression level [0-9]. 0 means no compression, 9 means maximum compression")
    ;
    return optionDescriptor;
}

} // unnamed namespace

std::unique_ptr<boost::program_options::variables_map>
parseArguments(int argc, char* argv[])
{
    auto optionDescriptor = describeArguments();

    auto result = std::make_unique<boost::program_options::variables_map>();
    boost::program_options::store(
        boost::program_options::parse_command_line(
            argc, argv, *optionDescriptor),
        *result);
    boost::program_options::notify(*result);

    if (result->count("help")) {
        std::cout << *optionDescriptor << "\n";
        return std::unique_ptr<boost::program_options::variables_map>();
    } else {
        return result;
    }
}
