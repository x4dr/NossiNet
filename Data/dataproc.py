import numpy
from dask.distributed import Client
from numba import njit


@njit(parallel=True)
def sort(x):
    x = numpy.array([(10 * y) for y in x], "int32")
    return numpy.sort(x)


c = Client("tcp://localhost:8786")

e = []
for i in range(10):
    e.append((i, c.submit(sort, c.submit(numpy.random.random, 50))))

for li in e:
    print(c.gather(li))
