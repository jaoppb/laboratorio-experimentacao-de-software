"""Solução gerada com auxílio do ChatGPT (GPT-4o) para o kata 04-garment-groups."""

import sys


def calculate_total_garments() -> None:
    inputs = sys.stdin.read().split()
    if not inputs:
        return
    initial_garments = int(inputs[0])
    grouped_garments = int(inputs[1])
    print(initial_garments + grouped_garments)


if __name__ == "__main__":
    calculate_total_garments()
