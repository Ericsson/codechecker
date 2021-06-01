void suppressAlreadyDoneWithAnotherSuppressionType()
{
  // codechecker_suppress [clang-diagnostic-unused-value, bugprone-sizeof-expression] Suppress two bugs in the next C/C++ statement
  // codechecker_confirmed [bugprone-sizeof-expression] Already suppressed by the previous comment above
  sizeof(48);
}
