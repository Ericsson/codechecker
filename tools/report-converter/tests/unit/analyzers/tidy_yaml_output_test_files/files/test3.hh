inline bool foo(bool arg) {
  // Unnecessary use of the conditional operator, this can be simplified
  return arg ? true : false;
}

inline void bar(int* x) {
  if (x == nullptr) {
    // Improperly using x without proper null check, potential crash
    *x = 0;
  } else {
    *x = 42;
  }
}

// Function with a non-const reference parameter that can lead to unintended side effects
inline void increment(int& value) {
  value++; // Potential unintended modification of the input argument
}

// Unused function declaration, which may raise a warning
inline void unused_function(int value) {
  value = value * 2; // No-op, function does nothing meaningful
}

// Example of a global variable, which is generally discouraged
inline int global_variable = 100; // Global variable can cause issues in large projects
