# life_tables.jl — US SSA 2021 and UK ONS 2020-2022 mortality tables
# Source: SSA Actuarial Life Tables 2021, ONS National Life Tables 2020-2022

# US Male (single-year ages 30-99)
const US_MALE_AGES = Int[
    30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,
    50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,
    70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,
    90,91,92,93,94,95,96,97,98,99]
const US_MALE_QX = Float64[
    0.00143,0.00149,0.00157,0.00166,0.00176,0.00186,0.00196,0.00207,0.00218,0.00230,
    0.00242,0.00255,0.00270,0.00287,0.00306,0.00327,0.00352,0.00380,0.00411,0.00446,
    0.00485,0.00528,0.00575,0.00627,0.00684,0.00747,0.00816,0.00891,0.00972,0.01059,
    0.01152,0.01252,0.01360,0.01477,0.01604,0.01743,0.01896,0.02065,0.02251,0.02455,
    0.02679,0.02925,0.03195,0.03493,0.03820,0.04181,0.04580,0.05021,0.05510,0.06052,
    0.06653,0.07322,0.08068,0.08899,0.09824,0.10854,0.12000,0.13271,0.14679,0.16233,
    0.17945,0.19823,0.21874,0.24105,0.26520,0.29122,0.31908,0.34872,0.38004,0.41290]

# US Female
const US_FEMALE_AGES = US_MALE_AGES  # same age range
const US_FEMALE_QX = Float64[
    0.00082,0.00086,0.00091,0.00097,0.00104,0.00111,0.00119,0.00127,0.00136,0.00146,
    0.00157,0.00169,0.00182,0.00196,0.00211,0.00228,0.00248,0.00270,0.00294,0.00320,
    0.00349,0.00381,0.00416,0.00454,0.00496,0.00541,0.00590,0.00643,0.00700,0.00762,
    0.00829,0.00902,0.00982,0.01070,0.01166,0.01272,0.01390,0.01520,0.01664,0.01824,
    0.02000,0.02195,0.02412,0.02653,0.02921,0.03220,0.03555,0.03932,0.04357,0.04839,
    0.05386,0.06010,0.06722,0.07536,0.08465,0.09525,0.10729,0.12094,0.13635,0.15368,
    0.17309,0.19469,0.21863,0.24500,0.27391,0.30541,0.33951,0.37619,0.41535,0.45684]

# UK Male (5-year intervals)
const UK_MALE_AGES = Int[30,35,40,45,50,55,60,65,70,75,80,85,90,95,99]
const UK_MALE_QX  = Float64[
    0.00092,0.00108,0.00162,0.00252,0.00389,0.00598,0.00915,0.01380,
    0.02158,0.03510,0.05897,0.10118,0.17098,0.27832,0.38000]

# UK Female
const UK_FEMALE_AGES = UK_MALE_AGES
const UK_FEMALE_QX  = Float64[
    0.00052,0.00068,0.00102,0.00165,0.00252,0.00385,0.00579,0.00895,
    0.01433,0.02410,0.04318,0.08011,0.14583,0.25291,0.36000]

"""
    get_annual_mortality(age, sex, country) -> Float64

Get annual mortality qx with linear interpolation between table ages.
`country`: 0=US, 1=UK.
"""
@inline function get_annual_mortality(age::Float64, sex::Int8, country::Int8)::Float64
    if country == Int8(0)
        ages = sex == SEX_MALE ? US_MALE_AGES : US_FEMALE_AGES
        qx   = sex == SEX_MALE ? US_MALE_QX  : US_FEMALE_QX
    else
        ages = sex == SEX_MALE ? UK_MALE_AGES : UK_FEMALE_AGES
        qx   = sex == SEX_MALE ? UK_MALE_QX  : UK_FEMALE_QX
    end

    n = length(ages)
    if age <= ages[1]
        return qx[1]
    end
    if age >= ages[n]
        return qx[n]
    end

    # Find bracketing indices via linear scan (tables are short)
    lower_idx = 1
    for i in 1:n
        if ages[i] <= age
            lower_idx = i
        else
            break
        end
    end
    upper_idx = lower_idx + 1
    if upper_idx > n
        return qx[n]
    end

    frac = (age - ages[lower_idx]) / (ages[upper_idx] - ages[lower_idx])
    return qx[lower_idx] * (1.0 - frac) + qx[upper_idx] * frac
end

@inline function get_monthly_mortality(age::Float64, sex::Int8, country::Int8)::Float64
    annual = get_annual_mortality(age, sex, country)
    return 1.0 - (1.0 - annual)^(1.0/12.0)
end
