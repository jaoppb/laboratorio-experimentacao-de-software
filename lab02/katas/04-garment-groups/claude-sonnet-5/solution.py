import sys


def main():
    data = sys.stdin.read().split()
    n = int(data[0])
    g = int(data[1])
    # Each group of size k needs k+1 pegs (k-1 shared pegs between
    # consecutive shirts, plus 2 end pegs). Summing over all groups:
    # sum(k_i) + G = N + G.
    print(n + g)


if __name__ == "__main__":
    main()
