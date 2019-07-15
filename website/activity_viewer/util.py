import sys
from datetime import datetime


def time_this(method):
    def timed(*args, **kw):
        start = datetime.now()
        result = method(*args, **kw)
        end = datetime.now()
        print(f'{method.__name__} took {end - start}')
        sys.stdout.flush()
        return result

    return timed
