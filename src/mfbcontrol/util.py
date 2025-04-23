
def max_value(value: float, max: float) -> float:
    m = abs(max)
    return limit_value(value, (m*-1), m)

def limit_value(value: float, min: float, max: float) -> float:
    if value > max:
        return max
    elif value < min:
        return min
    else:
        return value
