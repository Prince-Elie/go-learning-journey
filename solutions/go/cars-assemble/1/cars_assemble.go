package cars

// CalculateWorkingCarsPerHour calculates how many working cars are
// produced by the assembly line every hour.
func CalculateWorkingCarsPerHour(productionRate int, successRate float64) float64 {
	return (float64(productionRate) * successRate) / 100
}

// CalculateWorkingCarsPerMinute calculates how many working cars are
// produced by the assembly line every minute.
func CalculateWorkingCarsPerMinute(productionRate int, successRate float64) int {
	return int(CalculateWorkingCarsPerHour(productionRate, successRate)) / 60
}

// CalculateCost works out the cost of producing the given number of cars.
func CalculateCost(carsCount int) uint {
	var x uint
    if carsCount == 10{
        x = 95000
    }else if carsCount > 10 && (carsCount % 10) != 0{
        y := carsCount / 10
        x = (95000 * uint(y)) + (10000 * (uint(carsCount) % 10))
    }else if carsCount > 10 && (carsCount % 10) == 0 {
        x = (uint(carsCount) / 10) * 95000
    }else {
        x = uint(carsCount) * 10000
    }
    return x
}
