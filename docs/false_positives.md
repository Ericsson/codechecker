# False positives

CodeChecker is running static analysis tools on the code. Unfortunately, it is
not possible to create perfect tools. They might report correct code as
incorrect. These findings are called false positives. This document explains
how to deal with them. As a rule of thumb, whenever you encounter a
false positive finding using suppression should be only the last resort. Why?
Read on.

Having a false positive indicates that the analyzer does not understand some
properties of the code. Suppressing a result will not help its understanding.
Making the code more obvious for the tool, however, makes the analysis more
precise. As a bonus, such code is sometimes also more readable for developers.

This guide introduces tips and tricks how to make the code easier to analyze.

Table of Contents
=================
 * [What target to analyze?](#what-target-to-analyze)
 * [Infeasible path](#infeasible-path)
   * [Correlated conditions](#correlated-conditions)
   * [Partial functions](#partial-functions)
   * [Prefer standard functions](#prefer-standard-functions)
   * [Do not turn off `core` checks](#do-not-turn-off-core-checks)
   * [Suppress specific dead store warnings](#suppress-specific-dead-store-warnings)
   * [Alternative implementations](#alternative-implementations)
 * [Syntax based checks](#syntax-based-checks)
 * [Suppress or skip results](#suppress-or-skip-results)
   * [3rd party code](#third-party-code)
   * [Authored code](#authored-code)
   * [Unauthored code](#unauthored-code)

## <a name="what-target-to-analyze"></a> What target to analyze?

Usually, a project has multiple build targets for different purposes. There
might be multiple targets for multiple architectures, releases, debugging.

We advise to use the debug target to analyze the code. The reason is, debug
targets usually contain assertions, while release targets do not.
These assertions convey useful information to the analyzer.

The analyzer understands the standard assert macro. In case a project has
custom assertion mechanisms the corresponding functions should be annotated
both to improve precision and avoid false positives. For details read the
guide of the [analyzer](https://clang-analyzer.llvm.org/annotations.html#custom_assertions).


## <a name="infeasible-path"></a> Infeasible path

One of the most frequent source of false positives is analyzing infeasible 
execution path of the program. Every report on such a path is false positive.
There are a number of ways to help the analyzer detect which paths are not
possible to take. This document also has some examples to show these techniques
in action.

* Functions that never return should be annotated as `noreturn`
  (available since C++11)
* Functions that never return null pointers might be annotated appropriately
* Assertions can be added to help the analyzer detect more invariants
* Partial functions can be made more explicit
* Unreachable annotations should be added
* Prefer standard functions to custom solutions
* Do not turn off `core` checks

### <a name="correlated-conditions"></a> Correlated conditions

The analyzer might not be able to detect that two conditions are mutually 
exclusive. Let us consider the following false positive:

```cpp
int x = f();
if (condition A) {
  x = 0;
}
...
if (nontrivial condition) {
  g(5/x); // Division by zero warning.
}
```

It can be rewritten to as the following to suppress the warning:

```cpp
int x = f();
if (condition A) {
  x = 0;
}
...
if (nontrivial condition) {
  assert(!(condition A));
  g(5/x); // No warning.
}
```

### <a name="partial-functions"></a> Partial functions

Some functions only work on a set of possible input values. This precondition
is unknown to the analyzer unless it is expressed explicitly in the code.

Let us consider the following false positive:

```cpp
int f(MyEnum Val) {
  int x = 0;
  switch (Val) {
    case MyEnumA: x = 1; break;
    case MyEnumB: x = 5; break;
  }
  return 5/x; // Division by zero when Val == MyEnumC.
}
```

It can be rewritten to as the following to suppress the warning:

```cpp
int f(MyEnum Val) {
  int x = 0;
  switch (Val) {
    case MyEnumA: x = 1; break;
    case MyEnumB: x = 5; break;
    default: assert(false); break;
  }
  return 5/x; // No warning.
}
```

Other macros or builtins expressing unreachable code may be used.
Note that the rewritten code is also safer, since debug builds now check for
more precondition violations. 

### <a name="prefer-standard-functions"></a> Prefer standard functions

The analyzer models the behavior of some standard functions but it has
no knowledge about the semantics of custom made functions declared in a
library that compiled separately or not reached by the analyzer.

Let us consider the following false positive:

```cpp
int f() {
  const char *Str = "MyStr";
  int Val = 0;
  ...
  if (mystrlen(Str)) {
    Val = 1;
  }
  return 5 / Val; // Division by zero.
}
```

It can be rewritten to as the following to suppress the warning:

```cpp
int f() {
  const char *Str = "MyStr";
  int Val = 0;
  ...
  if (strlen(Str)) {
    Val = 1;
  }
  return 5 / Val; // No warning.
}
```

The result is easier to read for other developers who might not be familiar
with the custom version of the function. The standard library functions also
tend to be faster and more correct than custom solutions.

### <a name="do-not-turn-off-core-checks"></a> Do not turn off `core` checks

Checks in the static analyzer are usually not just reporting issues but
also help modelling language constructs and library functions. You should never
turn off checks from the `core` package.

### <a name="suppress-specific-dead-store-warnings"></a> Suppress specific dead store warnings

How to suppress a specific dead store warning from the Clang Static Analyzer
and more useful tips can be found [here](https://clang-analyzer.llvm.org/faq.html).
Alternatively, the `__clang_analyzer__` macro can be used to introduce usages.
Or sometimes macros just need to be cleaned up. Let us consider the following
example:

```cpp
void foo() {
  int x = 3; // Dead store warning.
#ifdef ABC
  dostuff(x);
#endif
}
```

It can be rewritten to as the following to suppress the warning:

```cpp
void foo() {
#ifdef ABC
  int x = 3; // No warning.
  dostuff(x);
#endif
}
```

### <a name="alternative-implementations"></a> Alternative implementations

If there are huge source of false positives due to the analyzer can not model a
function properly you could either disable the analyzer to analyze that
function or provide an alternative implementation that is easier to model
(i.e.: implementation without bitwise operation tricks). This can be achieved
using the `__clang_analyzer__` macro.

For example the following code:

```cpp
unsigned f(unsigned x) {
  return (x >> 1) & 1;
}
```

Could be rewritten as:

```cpp
#ifndef __clang_analyzer__
unsigned f(unsigned x) {
  return (x >> 1) & 1;
}
#else
unsigned f(unsigned x) {
  return (x / 2) % 2;
}
#endif
```

The implementation without the bit manipulation can be understood by
the analyzer better. Note that the compiler might generate the same code
for the two implementations, so it might make sense to use only the more
obvious one.

## <a name="syntax-based-checks"></a> Syntax based checks

Clang-Tidy has lots of useful syntax based checks. Some of these checks
find bug-prone code snippets. When these snippets are intentional, usually
there is a natural way to make the intent more explicit. Unfortunately,
it is hard to give a general guideline, because the details are different for
each check. The documentation of the check might contain hints how to
express intention more clearly. Let us look at an example:

  
```cpp
double f(int i) {
  return 32 / (2 + i); // Warning, integer division, loss of precision.
}
```

It can be rewritten to as the following to suppress the warning:

```cpp
double f(int i) {
  return (int)(32 / (2 + i)); // No warning, the intention is explicit.
}
```

The second version makes it clear even though the return value is a floating
point value the loss of precision during integer division is intentional.
Adding a comment why this is intentional would make this even clearer.
Such edits makes the code easier to understand for fellow developers. 

## <a name="suppress-or-skip-results"></a> Suppress or skip results

When none of the above works, we can still resort to suppressing a particular
finding. There are multiple ways to do this and it is important to choose the
right one.

### <a name="third-party-code"></a> 3rd party code

We usually have no control over 3rd party code and are not interested in the
findings in such code. CodeChecker supports skipping certain files
(or even directory trees) of the analyzed project.
This might also make the analysis faster. For details, see the
[user guide](user_guide.md#skip).

### <a name="authored-code"></a> Authored code

If you have control over the code we advise to use in source code suppression.
This has the advantage of the code and the suppression evolving together and
more reliable than other ways of suppression methods. Only suppress the results
from one specific check that found the issue. Always comment why a
finding is considered false positive! With a future version of the analyzer
these suppression comments might be no longer required. Comments might help in
the reevaluation. For details, see the [user guide](user_guide.md#suppression-code).

### <a name="unauthored-code"></a> Unauthored code

If you do not have control over the code for some reason you can suppress 
issues using the web user interface. 
