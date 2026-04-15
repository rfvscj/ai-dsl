f metrics(nums)
  = even_square_sum SFM(nums,_%2==0,_*_)
  = big_count CF(nums,_>10)
  = squares DFM(nums,_,_*_,_>0)
  r (even_square_sum, big_count, squares)

= sample [1, 2, 11, 12]
p metrics(sample)
