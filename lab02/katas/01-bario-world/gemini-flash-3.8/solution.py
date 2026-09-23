import sys


def solve():
    input_data = sys.stdin.read().split()
    if not input_data:
        return

    t = int(input_data[0])
    idx = 1
    out = []

    for _ in range(t):
        n = int(input_data[idx])
        s = input_data[idx + 1]
        idx += 2

        # Identifica as ilhas de blocos sólidos 'x'
        islands = []
        i = 0
        while i < n:
            if s[i] == 'x':
                start = i + 1
                while i < n and s[i] == 'x':
                    i += 1
                end = i
                islands.append((start, end))
            else:
                i += 1

        num_islands = len(islands)

        # Sem buracos: Bario corre até o fim sem gastar nenhum pulo
        if num_islands <= 1:
            out.append("0")
            continue

        target_start = islands[-1][0]

        s0, e0 = islands[0]
        r0 = 2 * e0 - s0 + 1
        if r0 >= target_start:
            out.append("1")
            continue

        cur_reach = r0
        jumps = 1
        cur_island = 1

        possible = True
        while cur_reach < target_start:
            next_reach = cur_reach
            advanced = False
            while cur_island < num_islands and islands[cur_island][0] <= cur_reach:
                advanced = True
                si, ei = islands[cur_island]
                reach_i = 2 * ei - si + 1
                if reach_i > next_reach:
                    next_reach = reach_i
                cur_island += 1

            if not advanced or next_reach <= cur_reach:
                possible = False
                break

            cur_reach = next_reach
            jumps += 1
            if cur_reach >= target_start:
                break

        if possible and cur_reach >= target_start:
            out.append(str(jumps))
        else:
            out.append("-1")

    sys.stdout.write("\n".join(out) + "\n")


if __name__ == "__main__":
    solve()
