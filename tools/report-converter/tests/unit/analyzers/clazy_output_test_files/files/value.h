#ifndef VALUE_H
#define VALUE_H

struct Value
{
    Value() = default;
    Value(const Value &other);
    ~Value();

    int data = 0;
};

#endif
