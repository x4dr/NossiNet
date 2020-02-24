import errno
import os
import random


class DescriptiveError(Exception):
    pass


def write_nonblocking(path, data):
    fd = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_NONBLOCK)
    if isinstance(data, str):
        data = data.encode("utf-8")
    os.write(fd, data)
    os.close(fd)


def read_nonblocking(path, bufferSize=100, timeout=.100):
    import time
    """
    implementation of a non-blocking read
    works with a named pipe or file
    errno 11 occurs if pipe is still written too, wait until some data
    is available
    """
    grace = True
    result = []
    pipe = None
    try:
        pipe = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        content = "".encode()
        while True:
            try:
                buf = os.read(pipe, bufferSize)
                if not buf:
                    break
                else:
                    content += buf
            except OSError as e:
                if e.errno == 11 and grace:
                    # grace period, first write to pipe might take some time
                    # further reads after opening the file are then successful
                    time.sleep(timeout)
                    grace = False
                else:
                    break
        content = content.decode()
        if content:
            line = content.split("\n")
            result.extend(line)

    except OSError as e:
        if e.errno == errno.ENOENT:
            pipe = None
        else:
            raise e
    finally:
        if pipe is not None:
            os.close(pipe)
    return result


def is_int(s: str) -> bool:
    try:
        int(s)
        return True
    except ValueError:
        return False


def sumdict(inp):
    result = 0
    try:
        for e in inp.keys():
            result += int(inp[e])
    except:
        result = sum(inp)
    return result


def d10(amt, diff, ones=True):  # faster than the WoDDice
    succ = 0
    anti = 0
    for i in range(amt):
        x = random.randint(1, 10)
        if x >= diff:
            succ += 1
        if ones and x == 1:
            anti += 1
    if anti > 0:
        if succ > anti:
            return succ - anti
        else:
            if succ > 0:
                return 0
            else:
                return 0 - anti
    else:
        return succ


'''
time1 = time()
res1 = []
times = 10000
for i in range(times):
    res1.append(d10(10, 10))
time2 = time()
#res2 = d10bulk(999, 10000)
time3 = time()
print("single fast:", sum(res1)/times, "successes and", time2 - time1, "seconds")
#print("bulkslow:", sum(res2), "successes and", time3 - time1, "seconds")
'''
