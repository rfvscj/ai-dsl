f even_square_sum(nums)
  = squares FM(nums,_%2==0,_*_)
  r S(squares)

= data [1, 2, 3, 4, 5, 6]
= result even_square_sum(data)
p result
