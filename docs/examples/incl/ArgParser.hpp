#ifndef ARGPARSER_HPP
#define ARGPARSER_HPP

#include <boost/program_options/variables_map.hpp>

std::unique_ptr<boost::program_options::variables_map>
parseArguments(int argc, char* argv[]);

#endif // ARGPARSER_HPP
