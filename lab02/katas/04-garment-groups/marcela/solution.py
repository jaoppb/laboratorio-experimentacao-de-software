import sys


def main() -> None:
    data = sys.stdin.read().split()
    if not data:
        return
    n, g = int(data[0]), int(data[1])
    print(n + g)


if __name__ == "__main__":
    main()
