package raindrops

import "strconv"


func Convert(number int) string {
    var value string
	if number%3 == 0{
	    value += "Pling"
	}
    if number%5 == 0 {
        value += "Plang"
    }
    if number%7 == 0 {
        value += "Plong"
    }
    if value == "" {
        value = strconv.Itoa(number)
    }
    return value
}
