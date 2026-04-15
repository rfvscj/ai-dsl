def even_squares(nums):
    return [x * x for x in nums if x % 2 == 0]


def odd_cubes(nums):
    return [x * x * x for x in nums if x % 2 != 0]


def positive_square_sum(nums):
    return sum(x * x for x in nums if x > 0)


def non_negative_count(nums):
    return sum(1 for x in nums if x >= 0)


def square_lookup(nums):
    return {x: x * x for x in nums if x >= 0}


def has_large(nums):
    return any(x > 50 for x in nums)


def all_small(nums):
    return all(x < 100 for x in nums)


data = [-7, -2, 0, 3, 4, 9, 12, 18, 51]
report = {
    "even_squares": even_squares(data),
    "odd_cubes": odd_cubes(data),
    "positive_square_sum": positive_square_sum(data),
    "non_negative_count": non_negative_count(data),
    "square_lookup": square_lookup(data),
    "has_large": has_large(data),
    "all_small": all_small(data),
}
print(report)
