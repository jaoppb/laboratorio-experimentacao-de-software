N = int(input())
values = list(map(int, input().split()))

removed_until = -1
cards = dict()
cards_set = set()

for i in range(N):
    card = values[i]
    if card in cards and cards[card] > removed_until:
        removed_until = cards[card]

    cards[card] = i
    cards_set.add(card)

    while cards[max(cards_set)] <= removed_until:
        cards_set.discard(max(cards_set))

    top = max(cards_set)
    print(top, cards[top] + 1)
