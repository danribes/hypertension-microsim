"""
Patient history analysis for dynamic risk modification.

Analyzes temporal patterns, event clustering, treatment response,
and comorbidity burden to provide sophisticated risk modifiers
that leverage the full power of individual-level microsimulation.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from enum import Enum
import math


class TrajectoryType(Enum):
    """eGFR trajectory classification."""
    RAPID_DECLINER = "rapid"      # >3 mL/min/year
    NORMAL_DECLINER = "normal"    # 1-3 mL/min/year
    SLOW_DECLINER = "slow"        # 0.5-1 mL/min/year
    STABLE = "stable"             # <0.5 mL/min/year
    INSUFFICIENT_DATA = "insufficient"


class TreatmentResponse(Enum):
    """BP control quality classification."""
    EXCELLENT = "excellent"  # SBP consistently <130
    GOOD = "good"           # SBP 130-139
    FAIR = "fair"           # SBP 140-149
    POOR = "poor"           # SBP ≥150


@dataclass
class ComorbidityBurden:
    """Structured comorbidity burden assessment."""
    charlson_score: int
    mental_health_burden: str  # "none", "mild", "moderate", "severe"
    substance_use_severity: str
    respiratory_burden: str
    interactive_effects: List[str]  # e.g., ["COPD+CVD", "Depression+Diabetes"]


class PatientHistoryAnalyzer:
    """
    Comprehensive patient history analysis for dynamic risk modification.
    
    Analyzes:
    1. Disease progression trajectories (eGFR, SBP over time)
    2. Event clustering patterns
    3. Treatment response quality
    4. Comorbidity burden and interactions
    5. Adherence patterns
    
    This module is the key differentiator between microsimulation and Markov models,
    leveraging full patient history to provide clinically-realistic risk modifiers.
    """
    
    def __init__(self, patient):
        """Initialize analyzer with patient object."""
        self.patient = patient
        self.history = patient.event_history
        self.current_time = patient.time_in_simulation
    
    # ========================================
    # Primary Risk Modifier Methods
    # ========================================
    
    def get_cvd_risk_modifier(self) -> float:
        """
        Calculate CVD risk modifier based on full patient history.
        
        Combines:
        - Prior CVD events (with time decay)
        - Event clustering
        - Comorbidity burden
        - Treatment response quality
        - Substance use/mental health
        
        Returns:
            Multiplicative modifier for base Framingham risk (1.0 = no change)
        """
        modifier = 1.0
        
        # 1. Prior events with time decay
        modifier *= self._prior_cvd_modifier()
        
        # 2. Event clustering (high risk)
        if self._has_event_clustering(event_type='CVD', window_months=60):
            modifier *= 1.8  # Clustered events = unstable patient
        
        # 3. Comorbidity interactions
        modifier *= self._comorbidity_cvd_modifier()
        
        # 4. Treatment response (poor control = higher risk)
        response = self.classify_bp_control()
        response_modifiers = {
            TreatmentResponse.EXCELLENT: 0.85,
            TreatmentResponse.GOOD: 1.0,
            TreatmentResponse.FAIR: 1.2,
            TreatmentResponse.POOR: 1.5
        }
        modifier *= response_modifiers.get(response, 1.0)
        
        # 5. Mental health / substance use
        if self.patient.has_depression and not self.patient.depression_treated:
            modifier *= 1.3  # Untreated depression increases CVD risk
        
        if self.patient.has_substance_use_disorder:
            modifier *= 1.8  # Substance use strongly increases CVD risk
        
        return modifier
    
    def get_renal_progression_modifier(self) -> float:
        """
        Calculate renal progression modifier based on eGFR trajectory.
        
        Returns:
            Multiplicative modifier for base eGFR decline rate
        """
        modifier = 1.0
        
        # 1. Historical trajectory
        trajectory = self.classify_egfr_trajectory()
        trajectory_modifiers = {
            TrajectoryType.RAPID_DECLINER: 1.5,
            TrajectoryType.NORMAL_DECLINER: 1.0,
            TrajectoryType.SLOW_DECLINER: 0.8,
            TrajectoryType.STABLE: 0.6,
            TrajectoryType.INSUFFICIENT_DATA: 1.0
        }
        modifier *= trajectory_modifiers[trajectory]
        
        # 2. Albuminuria progression
        if self._has_progressing_albuminuria():
            modifier *= 1.4
        
        # 3. Comorbidity burden
        if self.patient.has_diabetes and (
            self.patient.prior_mi_count > 0 or self.patient.prior_stroke_count > 0
        ):
            modifier *= 1.3  # Synergistic effect
        
        if self.patient.has_copd:
            modifier *= 1.2  # COPD accelerates CKD
        
        # 4. Treatment adherence pattern
        if self._has_poor_adherence_pattern():
            modifier *= 1.3
        
        return modifier
    
    def get_mortality_risk_modifier(self) -> float:
        """
        Calculate mortality risk modifier based on comorbidity burden.
        
        Uses Charlson-like scoring with additional factors.
        """
        modifier = 1.0
        
        # 1. Charlson Comorbidity Index
        charlson = self._calculate_charlson_score()
        # Each point adds ~10% mortality risk
        modifier *= (1.0 + charlson * 0.10)
        
        # 2. Specific high-risk comorbidities
        if self.patient.has_copd:
            if self.patient.copd_severity == "severe":
                modifier *= 2.5
            elif self.patient.copd_severity == "moderate":
                modifier *= 1.8
            else:
                modifier *= 1.4
        
        if self.patient.has_substance_use_disorder:
            modifier *= 2.0  # High mortality risk
        
        if self.patient.has_serious_mental_illness:
            modifier *= 1.6
        
        # 3. Event clustering
        recent_events = self._count_events_in_window('any', 12)
        if recent_events >= 2:
            modifier *= 1.5
        
        return modifier
    
    def get_adherence_probability_modifier(self) -> float:
        """
        Modify base adherence probability based on mental health.
        
        Returns:
            Multiplicative modifier for baseline adherence probability
        """
        modifier = 1.0
        
        if self.patient.has_depression:
            modifier *= 0.7 if not self.patient.depression_treated else 0.9
        
        if self.patient.has_anxiety:
            modifier *= 0.85
        
        if self.patient.has_substance_use_disorder:
            modifier *= 0.5  # Major adherence barrier
        
        if self.patient.has_serious_mental_illness:
            modifier *= 0.6
        
        return modifier
    
    # ========================================
    # Trajectory Classification Methods
    # ========================================
    
    def classify_egfr_trajectory(self) -> TrajectoryType:
        """
        Classify rate of eGFR decline over past 12-24 months.
        
        Returns:
            TrajectoryType enum
        """
        egfr_events = [e for e in self.history if 'egfr' in e]
        
        if len(egfr_events) < 12:
            return TrajectoryType.INSUFFICIENT_DATA
        
        # Use recent 24 months or all available
        lookback = min(24, len(egfr_events))
        recent = egfr_events[-lookback:]
        
        # Calculate slope (mL/min/month)
        times = [e['time'] for e in recent]
        egfrs = [e['egfr'] for e in recent]
        
        slope = self._calculate_slope(times, egfrs)
        annual_decline = abs(slope) * 12
        
        if annual_decline > 3.0:
            return TrajectoryType.RAPID_DECLINER
        elif annual_decline > 1.0:
            return TrajectoryType.NORMAL_DECLINER
        elif annual_decline > 0.5:
            return TrajectoryType.SLOW_DECLINER
        else:
            return TrajectoryType.STABLE
    
    def classify_bp_control(self) -> TreatmentResponse:
        """
        Classify BP control quality over past 6 months.
        
        Returns:
            TreatmentResponse enum
        """
        sbp_events = [e for e in self.history if 'sbp' in e]
        
        if len(sbp_events) < 3:
            return TreatmentResponse.FAIR  # Default assumption
        
        recent_sbp = [e['sbp'] for e in sbp_events[-6:]]
        avg_sbp = sum(recent_sbp) / len(recent_sbp)
        
        if avg_sbp < 130:
            return TreatmentResponse.EXCELLENT
        elif avg_sbp < 140:
            return TreatmentResponse.GOOD
        elif avg_sbp < 150:
            return TreatmentResponse.FAIR
        else:
            return TreatmentResponse.POOR
    
    def assess_comorbidity_burden(self) -> ComorbidityBurden:
        """
        Comprehensive comorbidity burden assessment.
        
        Returns:
            ComorbidityBurden dataclass with structured scores
        """
        charlson = self._calculate_charlson_score()
        
        # Mental health burden
        mh_count = sum([
            self.patient.has_depression,
            self.patient.has_anxiety,
            self.patient.has_serious_mental_illness
        ])
        if mh_count >= 2:
            mh_burden = "severe"
        elif mh_count == 1 and (
            self.patient.has_serious_mental_illness or 
            (self.patient.has_depression and not self.patient.depression_treated)
        ):
            mh_burden = "moderate"
        elif mh_count == 1:
            mh_burden = "mild"
        else:
            mh_burden = "none"
        
        # Substance use severity
        if self.patient.has_substance_use_disorder:
            if self.patient.substance_type == "poly":
                su_severity = "severe"
            elif self.patient.substance_type in ["opioids", "stimulants"]:
                su_severity = "moderate"
            else:
                su_severity = "mild"
        else:
            su_severity = "none"
        
        # Respiratory burden
        if self.patient.has_copd:
            resp_burden = self.patient.copd_severity or "moderate"
        else:
            resp_burden = "none"
        
        # Interactive effects
        interactions = []
        if self.patient.has_copd and (self.patient.prior_mi_count > 0 or self.patient.prior_stroke_count > 0):
            interactions.append("COPD+CVD")
        if self.patient.has_depression and self.patient.has_diabetes:
            interactions.append("Depression+Diabetes")
        if self.patient.has_substance_use_disorder and self.patient.has_heart_failure:
            interactions.append("SubstanceUse+HF")
        
        return ComorbidityBurden(
            charlson_score=charlson,
            mental_health_burden=mh_burden,
            substance_use_severity=su_severity,
            respiratory_burden=resp_burden,
            interactive_effects=interactions
        )
    
    # ========================================
    # Helper Methods
    # ========================================
    
    def _prior_cvd_modifier(self) -> float:
        """Calculate modifier based on prior CVD events with time decay."""
        modifier = 1.0
        
        # Prior MI
        if self.patient.prior_mi_count > 0:
            # First MI increases risk by 50%, each additional by 30%
            modifier *= (1.5 + (self.patient.prior_mi_count - 1) * 0.3)
        
        # Prior stroke
        if self.patient.prior_stroke_count > 0:
            modifier *= (1.4 + (self.patient.prior_stroke_count - 1) * 0.25)
        
        # Time decay (risk decreases over time)
        if self.patient.time_since_last_cv_event is not None:
            # Risk decays exponentially: e^(-0.05 * months)
            decay_factor = math.exp(-0.05 * self.patient.time_since_last_cv_event)
            # Apply decay only to the excess risk
            excess_risk = modifier - 1.0
            modifier = 1.0 + (excess_risk * decay_factor)
        
        return modifier
    
    def _comorbidity_cvd_modifier(self) -> float:
        """CVD risk modifier from comorbidities."""
        modifier = 1.0
        
        if self.patient.has_copd:
            modifier *= 1.5
        
        if self.patient.has_atrial_fibrillation:
            modifier *= 2.0  # Strong predictor
        
        if self.patient.has_peripheral_artery_disease:
            modifier *= 2.5  #Marker of severe atherosclerosis
        
        if self.patient.is_current_alcohol_user:
            modifier *= 1.3
        
        return modifier
    
    def _has_event_clustering(self, event_type: str, window_months: int) -> bool:
        """Check if patient has event clustering (3+ events in window)."""
        count = self._count_events_in_window(event_type, window_months)
        return count >= 3
    
    def _count_events_in_window(self, event_type: str, window_months: int) -> int:
        """Count events of specific type in recent window."""
        cutoff_time = self.current_time - window_months if self.current_time > window_months else 0
        
        if event_type == 'CVD':
            event_keywords = ['MI', 'Stroke', 'PAD', 'HF']
        elif event_type == 'any':
            event_keywords = ['MI', 'Stroke', 'PAD', 'HF', 'CKD']
        else:
            event_keywords = [event_type]
        
        count = 0
        for event in self.history:
            if event.get('time', 0) >= cutoff_time:
                event_name = event.get('event', '')
                if any(keyword in event_name for keyword in event_keywords):
                    count += 1
        
        return count
    
    def _has_progressing_albuminuria(self) -> bool:
        """Check if uACR has doubled over time."""
        uacr_events = [e for e in self.history if 'uacr' in e and e.get('uacr') is not None]
        
        if len(uacr_events) < 2:
            return False
        
        initial_uacr = uacr_events[0]['uacr']
        recent_uacr = sum(e['uacr'] for e in uacr_events[-3:]) / min(3, len(uacr_events[-3:]))
        
        return recent_uacr > 2.0 * initial_uacr
    
    def _has_poor_adherence_pattern(self) -> bool:
        """Detect poor adherence from SBP fluctuations."""
        sbp_events = [e for e in self.history if 'sbp' in e]
        
        if len(sbp_events) < 6:
            return False
        
        recent_sbp = [e['sbp'] for e in sbp_events[-6:]]
        variance = self._calculate_variance(recent_sbp)
        
        # High variance suggests inconsistent adherence
        return variance > 400  # SD > 20 mmHg
    
    def _calculate_charlson_score(self) -> int:
        """
        Calculate adapted Charlson Comorbidity Index.
        
        Charlson weights:
        - MI, CHF, PVD, CVD: 1 point each
        - COPD: 1 point
        - Diabetes without complications: 1 point
        - Diabetes with complications: 2 points
        - CKD moderate/severe: 2 points
        """
        score = 0
        
        # Cardiovascular (1 point each)
        if self.patient.prior_mi_count > 0:
            score += 1
        if self.patient.has_heart_failure:
            score += 1
        if self.patient.has_peripheral_artery_disease:
            score += 1
        if self.patient.prior_stroke_count > 0:
            score += 1
        
        # Diabetes
        if self.patient.has_diabetes:
            # Check for complications (CKD or CVD)
            has_complications = (
                self.patient.egfr < 60 or 
                self.patient.prior_mi_count > 0 or 
                self.patient.prior_stroke_count > 0
            )
            score += 2 if has_complications else 1
        
        # Renal disease
        if self.patient.egfr < 30:
            score += 2  # Severe CKD
        elif self.patient.egfr < 60:
            score += 1  # Moderate CKD
        
        # COPD
        if self.patient.has_copd:
            score += 1
        
        # Additional comorbidities
        if self.patient.has_substance_use_disorder:
            score += 2  # High mortality impact
        
        if self.patient.has_serious_mental_illness:
            score += 1
        
        return score
    
    def _calculate_slope(self, times: List[float], values: List[float]) -> float:
        """Simple linear regression slope."""
        n = len(times)
        if n < 2:
            return 0.0
        
        mean_time = sum(times) / n
        mean_value = sum(values) / n
        
        numerator = sum((times[i] - mean_time) * (values[i] - mean_value) for i in range(n))
        denominator = sum((times[i] - mean_time) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    def _calculate_variance(self, values: List[float]) -> float:
        """Calculate variance."""
        n = len(values)
        if n < 2:
            return 0.0
        
        mean = sum(values) / n
        return sum((x - mean) ** 2 for x in values) / (n - 1)
