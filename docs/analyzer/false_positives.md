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
     * [Loops](#loops)
     * [Prefer standard functions](#prefer-standard-functions)
     * [Use `const` whenever possible](#use-const)
     * [Do not turn off `core` checks](#do-not-turn-off-core-checks)
     * [Suppress specific dead store warnings](#suppress-specific-dead-store-warnings)
     * [Alternative implementations](#alternative-implementations)
  * [Defensive checks](#defensive-checks)
  * [Syntax based checks](#syntax-based-checks)
  * [Suppress or skip results](#suppress-or-skip-results)
     * [3rd party code](#third-party-code)
     * [Authored code](#authored-code)
     * [Unauthored code](#unauthored-code)

# What target to analyze? <a name="what-target-to-analyze"></a>

Usually, a project has multiple build targets for different purposes. There
might be multiple targets for multiple architectures, releases, debugging.

We advise to use the debug target to analyze the code. The reason is, debug
targets usually contain assertions, while release targets do not.
These assertions convey useful information to the analyzer.

The analyzer understands the standard assert macro. In case a project has
custom assertion mechanisms the corresponding functions should be annotated
both to improve precision and avoid false positives. For details read the
guide of the [analyzer](https://clang-analyzer.llvm.org/annotations.html#custom_assertions).


## Infeasible path <a name="infeasible-path"></a>

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

### Correlated conditions <a name="correlated-conditions"></a>

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

### Partial functions <a name="partial-functions"></a>

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

In case of C++11 or later, another option is to use Immediately-Invoked
Function Expression (IIFE) to avoid assigning a meaningless value.

```cpp
int f(MyEnum Val) {
  const int x = [&] { // Note the lambda.
    switch (Val) {
      case MyEnumA: return 1;
      case MyEnumB: return 5;
      default: assert(false); return 0;
    }
  } ();
  return 5/x; // No warning.
}
```

### Loops <a name="loops"></a>

Some loops are guaranteed to execute at least once and this is a dynamic
invariant of the program.
In some cases the analyzer cannot prove this property of a loop and it will
simulate the path when the loop is not executed at all. It can be due to the
lack of context or the code being too complex to the analyzer. 
This might result in false positives like uninitialized variables or division
by zero.

Let us look at the the following example:

```cpp
int avg(List *l) {
  int sum = 0;
  int count = 0;
  for(; l != NULL; l = l->next) {
    sum += l->data;
    ++count;
  }
  return sum/count; // Warning, division by zero.
}
```

Without a calling context the analyzer cannot know that `List` is guaranteed to
be at least one element long. We need an `assert` to tell the analyzer about
this invariant.

```cpp
int avg(List *l) {
  int sum = 0;
  int count = 0;
  assert(l != NULL);
  for(; l != NULL; l = l->next) {
    sum += l->data;
    ++count;
  }
  return sum/count; // No warning.
}
```

Adding the `assert` will make the code cleaner for the reader because it makes
an important invariant of the program explicit. Moreover, it will make the
false positive finding disappear. This will also provide the users of the code
with an explicit check in the debug build which can help find bugs.

In some cases the analyzer cannot reason about the possible values of
expressions due to some limitations of the constraint solver. In the code
example below the analyzer cannot record the constraint about a complex
expression.

```cpp
if (a > 1 && b > 1 && c > 1) {
  int ret;
  assert(a*b+c > 0);
  while (a*b+c > 0) {
    ret = 0;
    ...
  }
  return ret; // Warning, uninitialized value.
}
```

You can rewrite the code to reflect that there will always be at least one
iteration such as using a `do-while` loop or using `while(true)` and break
out from the loop.  
If you do not want to change the layout of the code,
introducing a new variable can suppress this problem.

```cpp
if (a > 1 && b > 1 && c > 1) {
  int ret;
  int cond = a*b+c;
  assert(cond > 0);
  while (cond > 0) {
    ret = 0;
    ...
  }
  return ret; // No warning.
}
```

Do not forget to update the body of the loop if necessary.

### Prefer standard functions <a name="prefer-standard-functions"></a>

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

### Use `const` whenever possible <a name="use-const"></a>

It is useful to tell the analyzer when the state is not going to change.
This will make the analysis more precise and the code more readable.
Mark methods that are not going to change the state of the object as `const`.

Also, avoid using global variables as they are harder to reason about.
Mark global constants as `const`.

Consider the following code:

```cpp
static char *allv[] = { "prog", "arg1", "arg2" };
static int allc = sizeof(allv) / sizeof(allv[0]);
static void f(void) {
  for (int i = 1; i < allc; i++) {
    const char *p = allv[i];  // Warning, out of bounds.
  }
}
```

Tha analyzer might not be able to tell that the value of `allc` is always
the same as the length of the array `allv`. Rewriting the code and marking
`allc` `const` will solve this issue.

```cpp
static char *allv[] = { "prog", "arg1", "arg2" };
static const int allc = sizeof(allv) / sizeof(allv[0]);
static void f(void) {
  for (int i = 1; i < allc; i++) {
    const char *p = allv[i];  // No warnings.
  }
}
```

### Do not turn off `core` checks <a name="do-not-turn-off-core-checks"></a>

Checks in the static analyzer are usually not just reporting issues but
also help modelling language constructs and library functions. You should never
turn off checks from the `core` package.

### Suppress specific dead store warnings <a name="suppress-specific-dead-store-warnings"></a>

How to suppress a specific dead store warning from the Clang Static Analyzer
and more useful tips can be found [here](https://clang-analyzer.llvm.org/faq.html).
Alternatively, the `__clang_analyzer__` macro can be used to introduce usages.
This macro is automatically defined when the code is analyzed using the Clang
Static Analyzer.
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

### Alternative implementations <a name="alternative-implementations"></a>

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

## Defensive checks <a name="defensive-checks"></a>

This section is an odd one because we describe a technique to reduce false
negatives rather than false positives. 

The preconditions of a function should not be violated by the callers.
For the working example we will look at an `strlen` implementation.
It is illegal to call `strlen` with a null pointer.

```cpp
int strlen(const char *c) {
  int res = 0;
  for(; *c != 0; ++c) // Warn! Null pointer dereference.
    ++res;
  return res;
}

int main() {
  return strlen(0);
}
```

The analyzer will be able to find the null dereference in the code above.
In some cases, however, the author of the functions adds defensive checks to
avoid crashes when some clients do not respect the precondition.

```cpp
int strlen(const char *c) {
  if (c == 0) {
    // Maybe set an error flag.
    return 0; // Or might throw exception in case of C++.
  }
  int res = 0;
  for(; *c != 0; ++c) // No warning.
    ++res;
  return res;
}

int main() {
  return strlen(0);
}
```

In the code above the analyzer will not be able to find any errors since it has
no way to tell whether the defensive checks are due to precondition 
violations or they are part of the defined behavior. This is called a false 
negative.

In order to reduce false negatives due to those safety checks we have several
options.

* We can state the precondition in the function signature. This is not always
 possible with the current language features.
```cpp
int strlen(const char * _Nonnull c);
```
* We can just omit the safety check. This might not be feasible in every 
scenario. But in case the only purpose of the check is debugging using 
sanitizers and other dynamic analysis tools is always a viable alternative.
* Guard the safety checks with a macro.
```cpp
int strlen(const char *c) {
#ifndef __clang_analyzer__
  if (c == 0)
    return 0;
#endif
  int res = 0;
  for(; *c != 0; ++c)
    ++res;
  return res;
}
```

As a rule of thumb always think whether a condition in a defensive check is
responsible for catching precondition violations or part of the defined 
behavior of the function. In the former case, make sure the check does 
compromise the static analysis. Excluding those checks from the analysis 
might not only increase the useful results from the analyzer but also reduce
the analysis time on that code.

## Syntax based checks <a name="syntax-based-checks"></a>

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

# Suppress or skip results <a name="suppress-or-skip-results"></a>

When none of the above works, we can still resort to suppressing a particular
finding. There are multiple ways to do this and it is important to choose the
right one.

## 3rd party code <a name="third-party-code"></a>

We usually have no control over 3rd party code and are not interested in the
findings in such code. CodeChecker supports skipping certain files
(or even directory trees) of the analyzed project.
This might also make the analysis faster. For details, see the
[user guide](user_guide.md#skip).

## Authored code <a name="authored-code"></a>

If you have control over the code we advise to use in source code suppression.
This has the advantage of the code and the suppression evolving together and
more reliable than other ways of suppression methods. Only suppress the results
from one specific check that found the issue. Always comment why a
finding is considered false positive! With a future version of the analyzer
these suppression comments might be no longer required. Comments might help in
the reevaluation. For details, see the
[user guide](user_guide.md#source-code-comments).

## Unauthored code <a name="unauthored-code"></a>

If you do not have control over the code for some reason you can suppress 
issues using the web user interface. 
