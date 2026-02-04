"""
Population generator for hypertension microsimulation.

Generates synthetic patient populations based on distributions
derived from clinical trial data and epidemiological studies.
"""

import numpy as np
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from .patient import Patient, Sex, Treatment, CardiacState, RenalState
from .risk_assessment import (
    calculate_gcua_phenotype,
    calculate_eocri_phenotype,
    calculate_kdigo_risk,
    calculate_framingham_risk,
    RiskInputs,
    BaselineRiskProfile
)


@dataclass
class PopulationParams:
    """
    Parameters for generating patient populations.

    Age Distribution Note:
        The default age range (40-85) can be modified to include younger adults
        (age_min=18) for populations requiring EOCRI stratification. The model
        supports a dual-branch architecture:
        - Age 18-59: EOCRI (Early-Onset Cardiorenal Risk Indicator)
        - Age 60+: GCUA (Geriatric Cardiorenal-Metabolic Unified Algorithm)
    """

    # Sample size
    n_patients: int = 1000

    # Age distribution (years)
    # Note: Set age_min=18 to include non-geriatric EOCRI population
    age_mean: float = 62.0
    age_sd: float = 10.0
    age_min: float = 40.0  # Can lower to 18 for EOCRI-eligible population
    age_max: float = 85.0
    
    # Sex distribution
    prop_male: float = 0.55
    
    # Blood pressure distribution (mmHg)
    # For resistant hypertension: elevated despite treatment
    sbp_mean: float = 155.0
    sbp_sd: float = 15.0
    sbp_min: float = 140.0  # Uncontrolled by definition
    sbp_max: float = 200.0
    
    dbp_mean: float = 92.0
    dbp_sd: float = 10.0
    
    # Renal function
    egfr_mean: float = 68.0
    egfr_sd: float = 20.0
    egfr_min: float = 15.0
    egfr_max: float = 120.0
    
    uacr_mean: float = 50.0
    uacr_sd: float = 80.0  # Log-normal distribution
    
    # Lipids
    total_chol_mean: float = 200.0
    total_chol_sd: float = 40.0
    hdl_chol_mean: float = 48.0
    hdl_chol_sd: float = 12.0
    
    # Comorbidity prevalence
    diabetes_prev: float = 0.35
    smoker_prev: float = 0.15
    dyslipidemia_prev: float = 0.60
    prior_mi_prev: float = 0.10
    prior_stroke_prev: float = 0.05
    heart_failure_prev: float = 0.08
    
    # BMI
    bmi_mean: float = 30.5
    bmi_sd: float = 5.5
    
    # Treatment
    mean_antihypertensives: int = 4
    adherence_prob: float = 0.75
    
    # Random seed
    seed: Optional[int] = None


class PopulationGenerator:
    """
    Generates patient populations for microsimulation.
    
    Uses correlated sampling to maintain realistic relationships
    between patient characteristics.
    """
    
    def __init__(self, params: Optional[PopulationParams] = None):
        """
        Initialize the population generator.
        
        Args:
            params: Population parameters. Uses defaults if None.
        """
        self.params = params or PopulationParams()
        self.rng = np.random.default_rng(self.params.seed)
    
    def generate(self) -> List[Patient]:
        """
        Generate a population of patients.
        
        Returns:
            List of Patient instances
        """
        n = self.params.n_patients
        patients = []
        
        # Generate correlated characteristics
        ages = self._sample_ages(n)
        sexes = self._sample_sexes(n)
        sbps = self._sample_sbps(n, ages)
        dbps = self._sample_dbps(n, sbps)
        egfrs = self._sample_egfrs(n, ages)
        uacrs = self._sample_uacrs(n, egfrs)
        
        # Lipids
        total_chols = self._sample_normal(
            n, self.params.total_chol_mean, self.params.total_chol_sd, 120, 350
        )
        hdl_chols = self._sample_normal(
            n, self.params.hdl_chol_mean, self.params.hdl_chol_sd, 20, 100
        )
        
        # BMI
        bmis = self._sample_normal(
            n, self.params.bmi_mean, self.params.bmi_sd, 18, 55
        )
        
        # Comorbidities (with correlations)
        has_diabetes = self._sample_comorbidity(n, self.params.diabetes_prev, bmis, ages)
        is_smoker = self.rng.binomial(1, self.params.smoker_prev, n).astype(bool)
        has_dyslipidemia = self.rng.binomial(1, self.params.dyslipidemia_prev, n).astype(bool)
        
        # Prior events (correlated with age and diabetes)
        prior_mi = self._sample_prior_events(n, self.params.prior_mi_prev, ages, has_diabetes)
        prior_stroke = self._sample_prior_events(n, self.params.prior_stroke_prev, ages, has_diabetes)
        has_hf = self._sample_prior_events(n, self.params.heart_failure_prev, ages, has_diabetes)
        
        # New comorbidities with clinical correlations
        
        # COPD (15-20% prevalence, higher in smokers)
        copd_prevalence = 0.17 + (0.15 * is_smoker)  # Smoking increases COPD risk
        has_copd = self.rng.binomial(1, copd_prevalence, n).astype(bool)
        copd_severity = []
        for i in range(n):
            if has_copd[i]:
                # Severity distribution: 40% mild, 40% moderate, 20% severe
                severity_roll = self.rng.random()
                if severity_roll < 0.4:
                    copd_severity.append("mild")
                elif severity_roll < 0.8:
                    copd_severity.append("moderate")
                else:
                    copd_severity.append("severe")
            else:
                copd_severity.append(None)
        
        # Depression (25-30%, higher in young females and diabetics)
        depression_prevalence = 0.27 * (
            (1 + 0.3 * (sexes == 0) * (ages < 65)) *  # Female and younger
            (1 + 0.2 * has_diabetes)  # Diabetes increases risk
        )
        depression_prevalence = depression_prevalence.clip(0, 0.5)
        has_depression = self.rng.binomial(1, depression_prevalence, n).astype(bool)
        depression_treated = self.rng.binomial(1, 0.60, n).astype(bool) * has_depression
        
        # Anxiety (15-20%, often comorbid with depression)
        anxiety_prevalence = 0.17 * (1 + 1.35 * has_depression)  # Higher if depressed
        anxiety_prevalence = anxiety_prevalence.clip(0, 0.5)
        has_anxiety = self.rng.binomial(1, anxiety_prevalence, n).astype(bool)
        
        # Substance use disorder (8-12%)
        has_substance_use = self.rng.binomial(1, 0.10, n).astype(bool)
        substance_type = []
        for i in range(n):
            if has_substance_use[i]:
                # Type distribution: 50% alcohol, 20% opioids, 15% stimulants, 15% poly
                type_roll = self.rng.random()
                if type_roll < 0.50:
                    substance_type.append("alcohol")
                elif type_roll < 0.70:
                    substance_type.append("opioids")
                elif type_roll < 0.85:
                    substance_type.append("stimulants")
                else:
                    substance_type.append("poly")
            else:
                substance_type.append(None)
        
        # Heavy alcohol use (separate from disorder, 15% prevalence)
        is_current_alcohol_user = self.rng.binomial(1, 0.15, n).astype(bool)
        
        # Serious mental illness (3-5%)
        has_smi = self.rng.binomial(1, 0.04, n).astype(bool)
        
        # Atrial fibrillation (10-15%, increases with age)
        afib_prevalence = 0.05 + (ages - 60).clip(0, 40) * 0.01  # Increases 1% per year after 60
        afib_prevalence = afib_prevalence.clip(0, 0.25)
        has_afib = self.rng.binomial(1, afib_prevalence, n).astype(bool)
        
        # PAD (12-18%, strongly linked to smoking and diabetes)
        pad_prevalence = 0.12 + 0.08 * is_smoker + 0.05 * has_diabetes
        pad_prevalence = pad_prevalence.clip(0, 0.30)
        has_pad = self.rng.binomial(1, pad_prevalence, n).astype(bool)

        # ============================================
        # Resistant Hypertension Specific Attributes
        # ============================================

        # Primary Aldosteronism (15-20% prevalence in resistant HTN)
        # Higher prevalence in patients with more severe HTN and obesity
        # Key target population for aldosterone synthase inhibitors (IXA-001)
        pa_base_prevalence = 0.17  # 17% baseline
        pa_prevalence = pa_base_prevalence * (
            1 + 0.2 * (sbps > 160)  # More severe HTN increases PA probability
            + 0.15 * (bmis >= 30)   # Obesity associated with PA
        )
        pa_prevalence = pa_prevalence.clip(0.10, 0.25)
        has_primary_aldosteronism = self.rng.binomial(1, pa_prevalence, n).astype(bool)

        # Years of uncontrolled hypertension (proxy from age and disease duration)
        # Resistant HTN patients have typically been uncontrolled for 3-10 years
        years_uncontrolled = self.rng.gamma(shape=3.0, scale=2.0, size=n)  # Mean ~6 years
        years_uncontrolled = np.clip(years_uncontrolled, 1, 15)
        
        # Adherence (Modified by Age and SDI)
        # Baseline probability from params, adjusted by risk factors
        # Young < 50: -15% adherence chance
        # High SDI > 75: -20% adherence chance
        
        # 1. Sample SDI (Social Deprivation Index, 0-100)
        # Using Beta distribution skewed slightly towards lower deprivation for general population
        sdi_scores = self.rng.beta(2, 2, n) * 100
        
        # 2. Calculate individual adherence probabilities
        adh_probs = np.full(n, self.params.adherence_prob)
        
        # Age effect (Young adults less adherent)
        adh_probs[ages < 50] -= 0.15
        
        # SDI effect (High deprivation less adherent)
        adh_probs[sdi_scores > 75] -= 0.20
        
        # Clip to [0.1, 0.95]
        adh_probs = np.clip(adh_probs, 0.1, 0.95)
        
        is_adherent = self.rng.binomial(1, adh_probs).astype(bool)
        
        # 3. Nocturnal Blood Pressure and Dipping Status
        # Categories: Normal (10-20% dip), Non-dipper (<10% dip), Reverse dipper (increase)
        nocturnal_sbps = []
        dipping_statuses = []
        
        for i in range(n):
            # Base probability of non-dipping increases with age and diabetes
            non_dip_prob = 0.25 + 0.005 * (ages[i] - 50) + 0.20 * has_diabetes[i]
            non_dip_prob = min(non_dip_prob, 0.80)
            
            dip_roll = self.rng.random()
            
            if dip_roll < non_dip_prob:
                # Non-dipper or Reverse dipper
                if self.rng.random() < 0.2: # 20% of non-dippers are reverse
                    status = "reverse_dipper"
                    # Nocturnal is 0-10% HIGHER than day
                    ratio = 1.0 + self.rng.uniform(0.0, 0.10)
                else:
                    status = "non_dipper"
                    # Nocturnal is 0-10% LOWER than day
                    ratio = 1.0 - self.rng.uniform(0.0, 0.10)
            else:
                status = "normal"
                # Nocturnal is 10-20% LOWER than day
                ratio = 1.0 - self.rng.uniform(0.10, 0.20)
            
            dipping_statuses.append(status)
            nocturnal_sbps.append(sbps[i] * ratio)
            
        # 4. White Coat Hypertension Effect
        # Research (e.g., IDACO) suggests ~20% prevalence of WCH in office hypertensives.
        # Mean effect: Office SBP is 10-20 mmHg HIGHER than True/Home BP.
        white_coat_effects = []
        is_wch_distribution = self.rng.binomial(1, 0.20, n).astype(bool) # 20% prevalence
        
        for i in range(n):
            if is_wch_distribution[i]:
                # WCH: Office is higher than True. Effect > 0.
                # Gamma dist to skew towards mild effect, but mean around 15 mmHg
                effect = self.rng.gamma(shape=3.0, scale=5.0) # Mean 15, SD ~8.6
                effect = max(5.0, min(40.0, effect)) # Clip reasonable bounds
            else:
                # Normotensive comparison / Sustained HTN -> small random noise
                # Office roughly equal to Home (mean 0 difference)
                effect = self.rng.normal(0, 2.0)
            
            white_coat_effects.append(effect)
            
        # 5. SGLT2 Inhibitor Usage (Guideline-Directed Medical Therapy - GDMT)
        # Class 1A for HF and CKD.
        # Uptake varies: approx 40-50% in good centers, lower in general practice.
        on_sglt2 = []
        for i in range(n):
            has_condition = (egfrs[i] < 60) or has_hf[i]
            if has_condition and self.rng.random() < 0.40: # 40% real-world uptake
                on_sglt2.append(True)
            else:
                on_sglt2.append(False)
        
        # Create patients
        for i in range(n):
            # Determine initial cardiac state
            c_state = CardiacState.NO_ACUTE_EVENT
            if has_hf[i]:
                c_state = CardiacState.CHRONIC_HF
            elif prior_stroke[i]:
                c_state = CardiacState.POST_STROKE
            elif prior_mi[i]:
                c_state = CardiacState.POST_MI
                
            # Determine initial renal state
            r_state = RenalState.CKD_STAGE_1_2
            if egfrs[i] < 15:
                r_state = RenalState.ESRD
            elif egfrs[i] < 30:
                r_state = RenalState.CKD_STAGE_4
            elif egfrs[i] < 45:
                r_state = RenalState.CKD_STAGE_3B
            elif egfrs[i] < 60:
                r_state = RenalState.CKD_STAGE_3A
            
            # Calculate baseline risk profile
            risk_inputs = RiskInputs(
                age=ages[i],
                sex="male" if sexes[i] else "female",
                egfr=egfrs[i],
                uacr=uacrs[i] if uacrs[i] > 0 else None,
                sbp=sbps[i],
                total_chol=total_chols[i],
                hdl_chol=hdl_chols[i],
                has_diabetes=has_diabetes[i],
                is_smoker=is_smoker[i],
                has_cvd=(prior_mi[i] or prior_stroke[i]),
                has_heart_failure=has_hf[i],
                bmi=bmis[i],
                is_on_bp_meds=True,  # All patients in study are on BP meds
                # New risk factors
                sdi_score=sdi_scores[i],
                nocturnal_sbp=nocturnal_sbps[i],
                # EOCRI-specific inputs
                has_dyslipidemia=has_dyslipidemia[i],
                has_obesity=(bmis[i] >= 30)
            )

            baseline_risk = BaselineRiskProfile()

            # ============================================
            # Dual-Branch Age-Based Risk Architecture
            # ============================================
            # Age >= 60: Route to GCUA (Geriatric pathway)
            # Age 18-59: Route to EOCRI (Non-geriatric pathway)
            # eGFR <= 60: Route to KDIGO (CKD pathway, regardless of age)

            if egfrs[i] > 60:
                # Branch based on age
                if ages[i] >= 60:
                    # GCUA pathway for geriatric patients (age 60+)
                    gcua = calculate_gcua_phenotype(risk_inputs)
                    if gcua['eligible']:
                        baseline_risk.renal_risk_type = "GCUA"
                        baseline_risk.gcua_phenotype = gcua['phenotype']
                        baseline_risk.gcua_phenotype_name = gcua['phenotype_name']
                        baseline_risk.gcua_nelson_risk = gcua['nelson_risk']
                        baseline_risk.gcua_cvd_risk = gcua['cvd_risk']
                        baseline_risk.gcua_mortality_risk = gcua['mortality_risk']
                        baseline_risk.risk_profile_confidence = gcua['confidence']
                elif ages[i] >= 18:
                    # EOCRI pathway for non-geriatric patients (age 18-59)
                    eocri = calculate_eocri_phenotype(risk_inputs)
                    if eocri['eligible']:
                        baseline_risk.renal_risk_type = "EOCRI"
                        baseline_risk.eocri_phenotype = eocri['phenotype']
                        baseline_risk.eocri_phenotype_name = eocri['phenotype_name']
                        baseline_risk.eocri_prevent_risk = eocri['prevent_risk']
                        baseline_risk.eocri_renal_progression_risk = eocri['renal_progression_risk']
                        baseline_risk.eocri_albuminuria_status = eocri['albuminuria_status']
                        baseline_risk.eocri_metabolic_burden = eocri['metabolic_burden']
                        baseline_risk.prevent_30yr_risk = eocri['prevent_risk']
                        # Categorize PREVENT risk
                        if eocri['prevent_risk'] < 10:
                            baseline_risk.prevent_risk_category = "Low"
                        elif eocri['prevent_risk'] < 20:
                            baseline_risk.prevent_risk_category = "Borderline"
                        elif eocri['prevent_risk'] < 40:
                            baseline_risk.prevent_risk_category = "Intermediate"
                        else:
                            baseline_risk.prevent_risk_category = "High"
                        baseline_risk.risk_profile_confidence = eocri['confidence']

            # KDIGO for CKD patients (eGFR <= 60) or if neither GCUA nor EOCRI eligible
            if baseline_risk.renal_risk_type == "KDIGO":
                kdigo = calculate_kdigo_risk(risk_inputs)
                baseline_risk.kdigo_gfr_category = kdigo['gfr_category']
                baseline_risk.kdigo_albuminuria_category = kdigo['albuminuria_category']
                baseline_risk.kdigo_risk_level = kdigo['risk_level']
                baseline_risk.risk_profile_confidence = kdigo['confidence']

            # Framingham CVD risk (all patients - for comparison)
            fram = calculate_framingham_risk(risk_inputs)
            baseline_risk.framingham_risk = fram['risk']
            baseline_risk.framingham_category = fram['category']

            # Primary aldosteronism (resistant HTN specific)
            baseline_risk.has_primary_aldosteronism = has_primary_aldosteronism[i]
            
            # Calculate Charlson score at baseline
            charlson = self._calculate_charlson_score(
                prior_mi=prior_mi[i],
                prior_stroke=prior_stroke[i],
                has_hf=has_hf[i],
                has_pad=has_pad[i],
                has_diabetes=has_diabetes[i],
                egfr=egfrs[i],
                has_copd=has_copd[i],
                has_substance_use=has_substance_use[i],
                has_smi=has_smi[i]
            )
            
            patient = Patient(
                patient_id=i,
                age=ages[i],
                sex=Sex.MALE if sexes[i] else Sex.FEMALE,
                baseline_sbp=sbps[i],
                baseline_dbp=dbps[i],
                current_sbp=sbps[i],
                current_dbp=dbps[i],
                egfr=egfrs[i],
                uacr=uacrs[i],
                total_cholesterol=total_chols[i],
                hdl_cholesterol=hdl_chols[i],
                has_diabetes=has_diabetes[i],
                is_smoker=is_smoker[i],
                has_dyslipidemia=has_dyslipidemia[i],
                bmi=bmis[i],
                # Respiratory
                has_copd=has_copd[i],
                copd_severity=copd_severity[i],
                # Substance use
                has_substance_use_disorder=has_substance_use[i],
                substance_type=substance_type[i],
                is_current_alcohol_user=is_current_alcohol_user[i],
                # Mental health
                has_depression=has_depression[i],
                depression_treated=depression_treated[i],
                has_anxiety=has_anxiety[i],
                has_serious_mental_illness=has_smi[i],
                # Additional CV risk factors
                has_atrial_fibrillation=has_afib[i],
                has_peripheral_artery_disease=has_pad[i],
                # Resistant HTN specific
                has_primary_aldosteronism=has_primary_aldosteronism[i],
                years_uncontrolled_htn=years_uncontrolled[i],
                # Comorbidity burden
                charlson_score=charlson,
                # Treatment and adherence
                num_antihypertensives=self.params.mean_antihypertensives,
                is_adherent=is_adherent[i],
                # New fields
                sdi_score=sdi_scores[i],
                nocturnal_sbp=nocturnal_sbps[i],
                nocturnal_dipping_status=dipping_statuses[i],
                adherence_history=[is_adherent[i]],
                
                # WCH
                white_coat_effect=white_coat_effects[i],
                
                # GDMT
                on_sglt2_inhibitor=on_sglt2[i],
                
                prior_mi_count=1 if prior_mi[i] else 0,
                prior_stroke_count=1 if prior_stroke[i] else 0,
                has_heart_failure=has_hf[i],
                # Disease states
                cardiac_state=c_state,
                renal_state=r_state,
                baseline_risk_profile=baseline_risk
            )
            patients.append(patient)
        
        return patients
    
    def _sample_ages(self, n: int) -> np.ndarray:
        """Sample ages with truncation."""
        return self._sample_normal(
            n, self.params.age_mean, self.params.age_sd,
            self.params.age_min, self.params.age_max
        )
    
    def _sample_sexes(self, n: int) -> np.ndarray:
        """Sample binary sex indicator (1=male, 0=female)."""
        return self.rng.binomial(1, self.params.prop_male, n)
    
    def _sample_sbps(self, n: int, ages: np.ndarray) -> np.ndarray:
        """Sample SBP with age correlation."""
        # SBP increases with age (~0.5 mmHg per year after 50)
        age_effect = np.maximum(0, (ages - 50) * 0.5)
        base_sbp = self._sample_normal(
            n, self.params.sbp_mean, self.params.sbp_sd,
            self.params.sbp_min, self.params.sbp_max
        )
        return np.clip(base_sbp + age_effect, self.params.sbp_min, self.params.sbp_max)
    
    def _sample_dbps(self, n: int, sbps: np.ndarray) -> np.ndarray:
        """Sample DBP correlated with SBP."""
        # DBP ~ 0.6 * SBP + noise
        base_dbp = sbps * 0.6 + self.rng.normal(0, 5, n)
        return np.clip(base_dbp, 60, 120)
    
    def _sample_egfrs(self, n: int, ages: np.ndarray) -> np.ndarray:
        """Sample eGFR with age correlation."""
        # eGFR decreases with age (~1 mL/min/year after 40)
        age_effect = np.maximum(0, (ages - 40) * 1.0)
        base_egfr = self._sample_normal(
            n, self.params.egfr_mean + 20, self.params.egfr_sd,
            self.params.egfr_min, self.params.egfr_max
        )
        return np.clip(base_egfr - age_effect, self.params.egfr_min, self.params.egfr_max)
    
    def _sample_uacrs(self, n: int, egfrs: np.ndarray) -> np.ndarray:
        """Sample UACR (log-normal, inversely correlated with eGFR)."""
        # Lower eGFR associated with higher UACR
        egfr_factor = np.maximum(0.5, (90 - egfrs) / 60)
        log_uacr = self.rng.normal(
            np.log(self.params.uacr_mean) + egfr_factor * 0.5,
            0.8, n
        )
        return np.clip(np.exp(log_uacr), 1, 3000)
    
    def _sample_comorbidity(
        self, n: int, base_prev: float, 
        bmis: np.ndarray, ages: np.ndarray
    ) -> np.ndarray:
        """Sample comorbidity with BMI and age correlation."""
        # Higher BMI and age increase diabetes risk
        bmi_factor = (bmis - 25) * 0.02
        age_factor = (ages - 50) * 0.005
        adjusted_prev = np.clip(base_prev + bmi_factor + age_factor, 0.05, 0.80)
        return self.rng.binomial(1, adjusted_prev).astype(bool)
    
    def _sample_prior_events(
        self, n: int, base_prev: float,
        ages: np.ndarray, has_diabetes: np.ndarray
    ) -> np.ndarray:
        """Sample prior CV events with age and diabetes correlation."""
        age_factor = (ages - 50) * 0.003
        diabetes_factor = has_diabetes.astype(float) * 0.05
        adjusted_prev = np.clip(base_prev + age_factor + diabetes_factor, 0.01, 0.50)
        return self.rng.binomial(1, adjusted_prev).astype(bool)
    
    def _calculate_charlson_score(
        self,
        prior_mi: bool,
        prior_stroke: bool,
        has_hf: bool,
        has_pad: bool,
        has_diabetes: bool,
        egfr: float,
        has_copd: bool,
        has_substance_use: bool,
        has_smi: bool
    ) -> int:
        """
        Calculate adapted Charlson Comorbidity Index at baseline.
        
        Returns:            Charlson score (0-15 typically)
        """
        score = 0
        
        # Cardiovascular (1 point each)
        if prior_mi:
            score += 1
        if has_hf:
            score += 1
        if has_pad:
            score += 1
        if prior_stroke:
            score += 1
        
        # Diabetes
        if has_diabetes:
            # Check for complications (CKD or CVD)
            has_complications = (egfr < 60 or prior_mi or prior_stroke)
            score += 2 if has_complications else 1
        
        # Renal disease
        if egfr < 30:
            score += 2  # Severe CKD
        elif egfr < 60:
            score += 1  # Moderate CKD
        
        # COPD
        if has_copd:
            score += 1
        
        # Additional comorbidities
        if has_substance_use:
            score += 2  # High mortality impact
        
        if has_smi:
            score += 1
        
        return score
    
    def _sample_normal(
        self, n: int, mean: float, sd: float, 
        min_val: float, max_val: float
    ) -> np.ndarray:
        """Sample from truncated normal distribution."""
        samples = self.rng.normal(mean, sd, n)
        return np.clip(samples, min_val, max_val)


def generate_default_population(
    n_patients: int = 1000,
    seed: Optional[int] = None
) -> List[Patient]:
    """
    Convenience function to generate a default population.
    
    Args:
        n_patients: Number of patients to generate
        seed: Random seed for reproducibility
        
    Returns:
        List of Patient instances
    """
    params = PopulationParams(n_patients=n_patients, seed=seed)
    generator = PopulationGenerator(params)
    return generator.generate()
