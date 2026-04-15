f fib(n)
  ? n < 2
    r n
  r fib(n - 1) + fib(n - 2)

= out [fib(i) for i in range(8)]
p out
