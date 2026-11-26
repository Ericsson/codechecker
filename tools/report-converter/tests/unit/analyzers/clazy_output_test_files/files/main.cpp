#include <QtCore/QMap>
#include <QtCore/QObject>
#include <QtCore/QString>
#include <QtCore/QTimer>

void connectTimer(QObject *receiver, QTimer *timer)
{
    QObject::connect(timer, SIGNAL(timeout()), receiver, SLOT(deleteLater()));
}

#include "value.h"

int sumValues(const QMap<QString, int> &map)
{
    int sum = 0;
    for (auto v : map.values())
        sum += v;
    return sum;
}

QString greeting()
{
    QString s = "hello";
    return s;
}
