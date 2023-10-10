# 3-Beyond-basics/bad-eval-with-code-flow.py

print("Hello, world!")
expr = input("Expression> ")
use_input(expr)


def use_input(raw_input):
    print(eval(raw_input))
