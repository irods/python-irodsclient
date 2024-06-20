#/usr/bin/env python3
import itertools
import sys
import typing

class too_many_results(Exception): pass
class too_few_results(Exception): pass

__all__ = ['first_n','one','too_many_results','too_few_results']

def first_n(iterable: typing.Iterable, n: int):
    return list(itertools.islice(iterable,n))

def one(iterable: typing.Iterable):
    i = first_n(iterable,2)
    if i[1:]:
        raise too_many_results
    if not i:
        raise too_few_results
    return i[0]

def test_one():
    assert(
            one(iter(range(10,10+i))) == 10
    )

def test_first_n():
    assert(
            first_n(iter(range(10,10+i)),2) == [10,11]
    )

if __name__=='__main__':
    test_one()
