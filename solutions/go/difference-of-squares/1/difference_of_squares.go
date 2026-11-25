package differenceofsquares

func SquareOfSum(n int) int {
	var total = 0
    for i := 0; i <= n; i++ {
        total += i
    }
    return total * total
}

func SumOfSquares(n int) int {
	var x = 0
    for i := 0; i <= n; i++ {
        x += i * i
    }
    return x
}

func Difference(n int) int {
	return SquareOfSum(n) - SumOfSquares(n)
}
