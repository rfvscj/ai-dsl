f even_squares(nums)
  r FM(nums,_%2==0,_*_)

f odd_cubes(nums)
  r FM(nums,_%2!=0,_*_*_)

f positive_square_sum(nums)
  r SFM(nums,_>0,_*_)

f non_negative_count(nums)
  r CF(nums,_>=0)

f square_lookup(nums)
  r DFM(nums,_,_*_,_>=0)

f has_large(nums)
  r A(nums,_>50)

f all_small(nums)
  r E(nums,_<100)

= data [-7, -2, 0, 3, 4, 9, 12, 18, 51]
= report {
  "even_squares": even_squares(data),
  "odd_cubes": odd_cubes(data),
  "positive_square_sum": positive_square_sum(data),
  "non_negative_count": non_negative_count(data),
  "square_lookup": square_lookup(data),
  "has_large": has_large(data),
  "all_small": all_small(data),
}
p report
