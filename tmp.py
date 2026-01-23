import random

COOLDOWN_ROLL_PDF = [10, 5, 3, 2, 1, 1, 3, 3, 3, 2, 1, 1, 1, 2, 2]
COOLDOWN_ROLL_TOTAL = sum(COOLDOWN_ROLL_PDF)


def roll_new_cooldown_strength():
    total = random.randint(0, COOLDOWN_ROLL_TOcTAL - 1)
    index = 0
    while total >= COOLDOWN_ROLL_PDF[index]:
        total -= COOLDOWN_ROLL_PDF[index]
        index += 1
    return index + 1


if __name__ == "__main__":
    acc = 0
    for i in range(10**7):
        acc += roll_new_cooldown_strength()
    print(acc, acc / (10**7))
