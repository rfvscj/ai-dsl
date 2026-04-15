def even_square_sum(nums):
    evens = [n for n in nums if n % 2 == 0]
    squares = [n * n for n in evens]
    return sum(squares)


data = [1, 2, 3, 4, 5, 6]
result = even_square_sum(data)
print(result)
