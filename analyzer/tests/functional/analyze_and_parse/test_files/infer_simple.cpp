#include <vector>
int foo(){
  const std::vector<int> vec;
  return vec[0]; // Empty vector access reported here
  // https://fbinfer.com/docs/all-issue-types#empty_vector_access
}