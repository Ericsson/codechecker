#include <QtCore/QString>

QString literal()
{
    int unused;
    QString s = "hello";
    return s;
}

int undeclared()
{
    return missing;
}
