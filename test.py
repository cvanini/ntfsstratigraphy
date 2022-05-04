import json
import more_itertools as mit

def test_algorithm(bitmap):
    free_spaces = [int(k) for k, v in bitmap.items() if v == 0]
    ranges = sorted([list(group) for group in mit.consecutive_groups(free_spaces)], key=lambda x: len(x))
    ranges = [f"[{x[0]}{'-' + str(x[-1]) if len(x) > 1 else ''}]" for x in ranges]
    return ranges

if __name__ == '__main__':
    r1 = [(2345, 33), (345678, 3), (234563, 345)]
    r2 = [(3, 123)]

    badclus = 300000
    d = {}

    b = []
    for i in r1:
        l = list(range(i[0], i[0]+i[1]+1))
        b.extend(l)

    bitmap = {0: 1, 1: 0, 2: 1, 3: 1, 4: 0, 5: 0, 6: 0, 7: 1, 8: 0, 9: 1, 10: 1, 11: 0, 12: 1}
    print(test_algorithm(bitmap))

