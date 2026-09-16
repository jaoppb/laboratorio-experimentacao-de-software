T = int(input())

for _ in range(T):
    N = int(input())

    line = input()
    blocks = []
    holes = []
    starts = []

    block = 0
    hole = 0
    last_hole_pos = -1
    for pos, c in enumerate(line):
        if c == '.':
            hole += 1
            last_hole_pos = pos
            if block > 0:
                blocks.append(block)
                block = 0
        elif c == 'x':
            if block == 0:
                starts.append(pos)
            block += 1
            if hole > 0:
                holes.append(hole)
                hole = 0

    blocks.append(block)
    holes.append(hole)

    if last_hole_pos == -1:
        print(0)
        continue

    target = N - 1
    jumps = 0
    cur_end = 0
    idx = 0
    possible = True

    while cur_end < target and cur_end <= last_hole_pos:
        farthest = -1

        while idx < len(blocks) and starts[idx] <= cur_end:
            reach = starts[idx] + 2 * blocks[idx] - 1
            if reach > farthest:
                farthest = reach
            idx += 1

        if farthest <= cur_end:
            possible = False
            break

        jumps += 1
        cur_end = min(farthest, target)

    print(jumps if possible else -1)
