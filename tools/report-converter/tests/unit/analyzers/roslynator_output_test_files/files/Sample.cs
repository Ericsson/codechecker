using System.Collections.Generic;
using System.Linq;

namespace files;

public class Sample
{
    // Triggers CA1822
    public int Add(int a, int b)
    {
        return a + b;
    }

    // Triggers CA1806
    public void AddOne(IEnumerable<int> enumerable)
    {
        enumerable.Select(n => Add(1, n));
    }
}
