#!/usr/bin/env python3
"""
Test script for baseline risk stratification.

Generates a sample population and reports the distribution of risk profiles.
"""

from src.population import generate_default_population
from collections import Counter

def main():
    print("="*70)
    print("BASELINE RISK STRATIFICATION VALIDATION")
    print("="*70)
    
    # Generate population
    print("\nGenerating population of 1,000 patients...")
    patients = generate_default_population(n_patients=1000, seed=42)
    print(f"✓ Generated {len(patients)} patients")
    
    print("\n" + "="*70)
    print("RISK PROFILE DISTRIBUTION")
    print("="*70)
    
    # Separate GCUA vs KDIGO
    gcua_patients = [p for p in patients if p.baseline_risk_profile.renal_risk_type == "GCUA"]
    kdigo_patients = [p for p in patients if p.baseline_risk_profile.renal_risk_type == "KDIGO"]
    
    print(f"\nRenal Risk Stratification:")
    print(f"  GCUA (age 60+, eGFR > 60): {len(gcua_patients)} ({100*len(gcua_patients)/len(patients):.1f}%)")
    print(f"  KDIGO (CKD or age < 60):   {len(kdigo_patients)} ({100*len(kdigo_patients)/len(patients):.1f}%)")
    
    # GCUA Phenotype Distribution
    if gcua_patients:
        print(f"\nGCUA Phenotype Distribution (n={len(gcua_patients)}):")
        phenotype_counts = Counter(p.baseline_risk_profile.gcua_phenotype for p in gcua_patients)
        for phenotype in ["I", "II", "III", "IV", "Moderate", "Low"]:
            count = phenotype_counts.get(phenotype, 0)
            pct = 100 * count / len(gcua_patients)
            name = gcua_patients[0].baseline_risk_profile.gcua_phenotype_name if count > 0 else ""
            
            # Find a sample patient
            sample = next((p for p in gcua_patients if p.baseline_risk_profile.gcua_phenotype == phenotype), None)
            if sample:
                nelson = sample.baseline_risk_profile.gcua_nelson_risk
                cvd = sample.baseline_risk_profile.gcua_cvd_risk
                mort = sample.baseline_risk_profile.gcua_mortality_risk
                print(f"  {phenotype} ({name}): {count:3d} ({pct:5.1f}%) "
                      f"[Sample: Nelson={nelson:.1f}%, CVD={cvd:.1f}%, Mort={mort:.1f}%]")
            else:
                print(f"  {phenotype}: {count:3d} ({pct:5.1f}%)")
    
    # KDIGO Risk Distribution
    if kdigo_patients:
        print(f"\nKDIGO Risk Distribution (n={len(kdigo_patients)}):")
        kdigo_risk_counts = Counter(p.baseline_risk_profile.kdigo_risk_level for p in kdigo_patients)
        for risk in ["Low", "Moderate", "High", "Very High"]:
            count = kdigo_risk_counts.get(risk, 0)
            pct = 100 * count / len(kdigo_patients)
            print(f"  {risk:12s}: {count:3d} ({pct:5.1f}%)")
        
        # GFR category breakdown
        print(f"\n  GFR Category Breakdown:")
        gfr_counts = Counter(p.baseline_risk_profile.kdigo_gfr_category for p in kdigo_patients)
        for cat in ["G1", "G2", "G3a", "G3b", "G4", "G5"]:
            count = gfr_counts.get(cat, 0)
            pct = 100 * count / len(kdigo_patients)
            print(f"    {cat}: {count:3d} ({pct:5.1f}%)")
    
    # Framingham CVD Risk Distribution (all patients)
    print(f"\nFramingham CVD Risk Distribution (n={len(patients)}):")
    fram_counts = Counter(p.baseline_risk_profile.framingham_category for p in patients)
    for category in ["Low", "Borderline", "Intermediate", "High"]:
        count = fram_counts.get(category, 0)
        pct = 100 * count / len(patients)
        
        # Sample patient data
        sample = next((p for p in patients if p.baseline_risk_profile.framingham_category == category), None)
        if sample:
            risk = sample.baseline_risk_profile.framingham_risk
            print(f"  {category:13s}: {count:3d} ({pct:5.1f}%) [Sample risk: {risk:.1f}%]")
        else:
            print(f"  {category:13s}: {count:3d} ({pct:5.1f}%)")
    
    # Cross-tabulation: GCUA Phenotype x Framingham CVD Risk
    if gcua_patients:
        print(f"\n" + "="*70)
        print("CROSS-TABULATION: GCUA Phenotype × Framingham CVD Risk")
        print("="*70)
        
        for phenotype in ["I", "II", "III", "Moderate", "Low"]:
            subset = [p for p in gcua_patients if p.baseline_risk_profile.gcua_phenotype == phenotype]
            if subset:
                fram_dist = Counter(p.baseline_risk_profile.framingham_category for p in subset)
                print(f"\nPhenotype {phenotype} (n={len(subset)}):")
                for fram_cat in ["Low", "Borderline", "Intermediate", "High"]:
                    count = fram_dist.get(fram_cat, 0)
                    pct = 100 * count / len(subset) if subset else 0
                    print(f"  {fram_cat:13s}: {count:2d} ({pct:4.1f}%)")
    
    # Sample patient profiles
    print(f"\n" + "="*70)
    print("SAMPLE PATIENT PROFILES")
    print("="*70)
    
    # High risk GCUA patient
    high_risk_gcua = next((p for p in gcua_patients if p.baseline_risk_profile.gcua_phenotype == "I"), None)
    if high_risk_gcua:
        r = high_risk_gcua.baseline_risk_profile
        print(f"\n1. High-Risk GCUA Patient (Phenotype I - Accelerated Ager):")
        print(f"   Age: {high_risk_gcua.age:.0f}, Sex: {high_risk_gcua.sex.value}, eGFR: {high_risk_gcua.egfr:.1f}")
        print(f"   Nelson (5y CKD risk): {r.gcua_nelson_risk:.1f}%")
        print(f"   Framingham (10y CVD): {r.framingham_risk:.1f}% ({r.framingham_category})")
        print(f"   Mortality (5y):       {r.gcua_mortality_risk:.1f}%")
        print(f"   → Dual high-risk phenotype requiring aggressive intervention")
    
    # Silent renal patient
    silent_renal = next((p for p    in gcua_patients if p.baseline_risk_profile.gcua_phenotype == "II"), None)
    if silent_renal:
        r = silent_renal.baseline_risk_profile
        print(f"\n2. Silent Renal Patient (Phenotype II):")
        print(f"   Age: {silent_renal.age:.0f}, Sex: {silent_renal.sex.value}, eGFR: {silent_renal.egfr:.1f}")
        print(f"   Nelson (5y CKD risk): {r.gcua_nelson_risk:.1f}%")
        print(f"   Framingham (10y CVD): {r.framingham_risk:.1f}% ({r.framingham_category})")
        print(f"   → High renal risk but low CVD (would be missed by Framingham-only screening)")
    
    # Very High KDIGO risk
    very_high_kdigo = next((p for p in kdigo_patients if p.baseline_risk_profile.kdigo_risk_level == "Very High"), None)
    if very_high_kdigo:
        r = very_high_kdigo.baseline_risk_profile
        print(f"\n3. Very High KDIGO Risk Patient:")
        print(f"   Age: {very_high_kdigo.age:.0f}, Sex: {very_high_kdigo.sex.value}, eGFR: {very_high_kdigo.egfr:.1f}")
        print(f"   KDIGO: {r.kdigo_gfr_category}  {r.kdigo_albuminuria_category} = {r.kdigo_risk_level}")
        print(f"   Framingham (10y CVD): {r.framingham_risk:.1f}% ({r.framingham_category})")
        print(f"   → Requires nephrology co-management and aggressive BP control")
    
    print(f"\n" + "="*70)
    print("✅ Validation Complete")
    print("="*70)

if __name__ == "__main__":
    main()
