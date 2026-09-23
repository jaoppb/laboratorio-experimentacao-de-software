import sys


def solve():
    input_data = sys.stdin.read().split()
    if not input_data:
        return

    n = int(input_data[0])
    g = int(input_data[1])

    # Em cada grupo de k camisas, o número de pregadores é k + 1.
    # Somando sobre os G grupos: sum(k_i + 1) = sum(k_i) + G = N + G.
    sys.stdout.write(f"{n + g}\n")


if __name__ == "__main__":
    solve()
