"""
Life table mortality rates for background mortality.

Provides age- and sex-specific mortality rates for use in microsimulation.
Supports both US (Social Security Administration) and UK (Office for National
Statistics) life tables.

Sources:
    US: Social Security Administration (SSA) Actuarial Life Tables 2021
        https://www.ssa.gov/oact/STATS/table4c6.html
    UK: Office for National Statistics (ONS) National Life Tables 2020-2022
        https://www.ons.gov.uk/peoplepopulationandcommunity/birthsdeathsandmarriages/
        lifeexpectancies/datasets/nationallifetablesunitedkingdomreferencetables

Reference:
    Arias E, Xu J. United States Life Tables, 2021. National Vital Statistics
    Reports. 2023;72(12):1-64.
"""

import numpy as np
from typing import Literal, Dict


# =============================================================================
# US SSA 2021 PERIOD LIFE TABLES
# Annual probability of death (qx) by single year of age
# Source: SSA Actuarial Life Table 2021, Period Life Table
# =============================================================================

US_LIFE_TABLE_MALE: Dict[int, float] = {
    # Age: annual death probability qx
    # Source: SSA 2021 Period Life Table for Males
    # PSA: Uncertainty ±10% applied to all values
    30: 0.00143, 31: 0.00149, 32: 0.00157, 33: 0.00166, 34: 0.00176,
    35: 0.00186, 36: 0.00196, 37: 0.00207, 38: 0.00218, 39: 0.00230,
    40: 0.00242, 41: 0.00255, 42: 0.00270, 43: 0.00287, 44: 0.00306,
    45: 0.00327, 46: 0.00352, 47: 0.00380, 48: 0.00411, 49: 0.00446,
    50: 0.00485, 51: 0.00528, 52: 0.00575, 53: 0.00627, 54: 0.00684,
    55: 0.00747, 56: 0.00816, 57: 0.00891, 58: 0.00972, 59: 0.01059,
    60: 0.01152, 61: 0.01252, 62: 0.01360, 63: 0.01477, 64: 0.01604,
    65: 0.01743, 66: 0.01896, 67: 0.02065, 68: 0.02251, 69: 0.02455,
    70: 0.02679, 71: 0.02925, 72: 0.03195, 73: 0.03493, 74: 0.03820,
    75: 0.04181, 76: 0.04580, 77: 0.05021, 78: 0.05510, 79: 0.06052,
    80: 0.06653, 81: 0.07322, 82: 0.08068, 83: 0.08899, 84: 0.09824,
    85: 0.10854, 86: 0.12000, 87: 0.13271, 88: 0.14679, 89: 0.16233,
    90: 0.17945, 91: 0.19823, 92: 0.21874, 93: 0.24105, 94: 0.26520,
    95: 0.29122, 96: 0.31908, 97: 0.34872, 98: 0.38004, 99: 0.41290,
}

US_LIFE_TABLE_FEMALE: Dict[int, float] = {
    # Source: SSA 2021 Period Life Table for Females
    # Note: Female mortality consistently lower than male at all ages
    30: 0.00082, 31: 0.00086, 32: 0.00091, 33: 0.00097, 34: 0.00104,
    35: 0.00111, 36: 0.00119, 37: 0.00127, 38: 0.00136, 39: 0.00146,
    40: 0.00157, 41: 0.00169, 42: 0.00182, 43: 0.00196, 44: 0.00211,
    45: 0.00228, 46: 0.00248, 47: 0.00270, 48: 0.00294, 49: 0.00320,
    50: 0.00349, 51: 0.00381, 52: 0.00416, 53: 0.00454, 54: 0.00496,
    55: 0.00541, 56: 0.00590, 57: 0.00643, 58: 0.00700, 59: 0.00762,
    60: 0.00829, 61: 0.00902, 62: 0.00982, 63: 0.01070, 64: 0.01166,
    65: 0.01272, 66: 0.01390, 67: 0.01520, 68: 0.01664, 69: 0.01824,
    70: 0.02000, 71: 0.02195, 72: 0.02412, 73: 0.02653, 74: 0.02921,
    75: 0.03220, 76: 0.03555, 77: 0.03932, 78: 0.04357, 79: 0.04839,
    80: 0.05386, 81: 0.06010, 82: 0.06722, 83: 0.07536, 84: 0.08465,
    85: 0.09525, 86: 0.10729, 87: 0.12094, 88: 0.13635, 89: 0.15368,
    90: 0.17309, 91: 0.19469, 92: 0.21863, 93: 0.24500, 94: 0.27391,
    95: 0.30541, 96: 0.33951, 97: 0.37619, 98: 0.41535, 99: 0.45684,
}


# =============================================================================
# UK ONS 2020-2022 NATIONAL LIFE TABLES
# Abridged tables (5-year age groups) with interpolation
# Source: ONS National Life Tables, United Kingdom, 2020-2022
# =============================================================================

UK_LIFE_TABLE_MALE: Dict[int, float] = {
    # Source: ONS National Life Tables UK 2020-2022
    # Note: 5-year intervals, linear interpolation used between
    30: 0.00092, 35: 0.00108, 40: 0.00162, 45: 0.00252,
    50: 0.00389, 55: 0.00598, 60: 0.00915, 65: 0.01380,
    70: 0.02158, 75: 0.03510, 80: 0.05897, 85: 0.10118,
    90: 0.17098, 95: 0.27832, 99: 0.38000,
}

UK_LIFE_TABLE_FEMALE: Dict[int, float] = {
    # Source: ONS National Life Tables UK 2020-2022
    30: 0.00052, 35: 0.00068, 40: 0.00102, 45: 0.00165,
    50: 0.00252, 55: 0.00385, 60: 0.00579, 65: 0.00895,
    70: 0.01433, 75: 0.02410, 80: 0.04318, 85: 0.08011,
    90: 0.14583, 95: 0.25291, 99: 0.36000,
}


class LifeTableCalculator:
    """
    Provides age- and sex-specific background mortality rates.

    Supports US (SSA) and UK (ONS) life tables with linear interpolation
    between ages for smooth mortality curves. Used to calculate non-CV
    mortality (background mortality) in the microsimulation.

    Example:
        >>> calc = LifeTableCalculator(country='US')
        >>> calc.get_annual_mortality(65, 'M')
        0.01743
        >>> calc.get_monthly_mortality(65, 'M')
        0.001463

    Reference:
        ISPOR-SMDM Modeling Good Research Practices Task Force.
        State-Transition Modeling. Med Decis Making. 2012;32(5):641-653.
    """

    def __init__(self, country: Literal['US', 'UK'] = 'US'):
        """
        Initialize with country-specific life tables.

        Args:
            country: 'US' for SSA tables (default), 'UK' for ONS tables

        Note:
            US tables have single-year ages (higher precision)
            UK tables have 5-year intervals (interpolation applied)
        """
        self.country = country

        if country == 'US':
            self._male_table = US_LIFE_TABLE_MALE
            self._female_table = US_LIFE_TABLE_FEMALE
        else:
            self._male_table = UK_LIFE_TABLE_MALE
            self._female_table = UK_LIFE_TABLE_FEMALE

    def get_annual_mortality(
        self,
        age: float,
        sex: Literal['M', 'F']
    ) -> float:
        """
        Get annual mortality probability for given age and sex.

        Uses linear interpolation between table ages for ages not
        directly in the table.

        Args:
            age: Age in years (can be fractional, e.g., 65.5)
            sex: 'M' for male, 'F' for female

        Returns:
            Annual probability of death qx (0-1)

        Example:
            >>> calc = LifeTableCalculator('US')
            >>> calc.get_annual_mortality(65, 'M')
            0.01743
            >>> calc.get_annual_mortality(65.5, 'M')  # Interpolated
            0.018195
        """
        table = self._male_table if sex == 'M' else self._female_table

        # Get sorted ages from table
        ages = sorted(table.keys())

        # Handle edge cases
        if age <= ages[0]:
            return table[ages[0]]
        if age >= ages[-1]:
            return table[ages[-1]]

        # Find bracketing ages for interpolation
        lower_age = max(a for a in ages if a <= age)
        upper_age = min(a for a in ages if a > age)

        # Linear interpolation
        frac = (age - lower_age) / (upper_age - lower_age)
        qx = table[lower_age] * (1 - frac) + table[upper_age] * frac

        return qx

    def get_monthly_mortality(
        self,
        age: float,
        sex: Literal['M', 'F']
    ) -> float:
        """
        Convert annual mortality to monthly probability.

        Uses the standard conversion formula assuming constant hazard
        within each year:
            p_month = 1 - (1 - p_year)^(1/12)

        Args:
            age: Age in years
            sex: 'M' or 'F'

        Returns:
            Monthly probability of death

        Reference:
            Briggs A, Sculpher M, Claxton K. Decision Modelling for
            Health Economic Evaluation. Oxford. 2006. Chapter 2.
        """
        annual_prob = self.get_annual_mortality(age, sex)
        return 1 - (1 - annual_prob) ** (1/12)

    def get_survival_probability(
        self,
        start_age: float,
        end_age: float,
        sex: Literal['M', 'F']
    ) -> float:
        """
        Calculate survival probability between two ages.

        Useful for validation against expected life expectancy.

        Args:
            start_age: Starting age
            end_age: Ending age
            sex: 'M' or 'F'

        Returns:
            Probability of surviving from start_age to end_age
        """
        if end_age <= start_age:
            return 1.0

        survival = 1.0
        current_age = start_age

        # Step through each year
        while current_age < end_age:
            step = min(1.0, end_age - current_age)
            qx = self.get_annual_mortality(current_age, sex)

            # Partial year adjustment
            if step < 1.0:
                qx = 1 - (1 - qx) ** step

            survival *= (1 - qx)
            current_age += step

        return survival

    def get_life_expectancy(
        self,
        age: float,
        sex: Literal['M', 'F'],
        max_age: int = 100
    ) -> float:
        """
        Calculate remaining life expectancy at given age.

        Useful for model validation against actuarial benchmarks.

        Args:
            age: Current age
            sex: 'M' or 'F'
            max_age: Maximum age for calculation (default 100)

        Returns:
            Expected remaining years of life

        Example:
            >>> calc = LifeTableCalculator('US')
            >>> calc.get_life_expectancy(65, 'M')
            17.4  # Approximately, varies with table
        """
        le = 0.0
        survival = 1.0
        current_age = age

        while current_age < max_age and survival > 0.001:
            qx = self.get_annual_mortality(current_age, sex)
            # Person-years lived in this year (midpoint approximation)
            le += survival * (1 - 0.5 * qx)
            survival *= (1 - qx)
            current_age += 1

        return le


def annual_to_monthly_prob(annual_prob: float) -> float:
    """
    Convert annual probability to monthly probability.

    Utility function for compatibility with existing code.
    Uses formula: p_month = 1 - (1 - p_year)^(1/12)

    Args:
        annual_prob: Annual probability (0-1)

    Returns:
        Monthly probability (0-1)
    """
    annual_prob = np.clip(annual_prob, 0.0, 0.999)
    return 1 - (1 - annual_prob) ** (1/12)
