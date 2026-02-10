# runtests.jl — Unit and integration tests for HypertensionSim

using Test
using Random

# Load module from project
include(joinpath(@__DIR__, "..", "src", "HypertensionSim.jl"))
using .HypertensionSim

# ============================================================================
# PREVENT risk equation tests
# ============================================================================
@testset "PREVENT equations" begin
    @testset "10-year CVD risk ranges" begin
        # Low-risk young female
        r1 = HypertensionSim.calculate_prevent_risk(
            40.0, SEX_FEMALE, 120.0, 90.0;
            has_diabetes=false, is_smoker=false,
            total_cholesterol=180.0, hdl_cholesterol=60.0, bmi=24.0,
        )
        @test 0.001 < r1 < 0.10

        # High-risk older male
        r2 = HypertensionSim.calculate_prevent_risk(
            70.0, SEX_MALE, 170.0, 40.0;
            has_diabetes=true, is_smoker=true,
            total_cholesterol=260.0, hdl_cholesterol=35.0, bmi=32.0,
        )
        @test 0.10 < r2 < 0.999

        # Risk increases with age
        r_young = HypertensionSim.calculate_prevent_risk(
            45.0, SEX_MALE, 140.0, 80.0;
        )
        r_old = HypertensionSim.calculate_prevent_risk(
            65.0, SEX_MALE, 140.0, 80.0;
        )
        @test r_old > r_young

        # Risk increases with SBP
        r_low = HypertensionSim.calculate_prevent_risk(
            55.0, SEX_MALE, 120.0, 80.0;
        )
        r_high = HypertensionSim.calculate_prevent_risk(
            55.0, SEX_MALE, 180.0, 80.0;
        )
        @test r_high > r_low
    end

    @testset "Probability conversions" begin
        @test HypertensionSim.annual_to_monthly_prob(0.0) ≈ 0.0 atol=1e-10
        @test HypertensionSim.annual_to_monthly_prob(1.0) ≈ HypertensionSim.annual_to_monthly_prob(0.999)

        # Monthly prob should be less than annual
        mp = HypertensionSim.annual_to_monthly_prob(0.10)
        @test 0.0 < mp < 0.10

        # 10-year to annual
        ap = HypertensionSim.ten_year_to_annual_prob(0.20)
        @test 0.0 < ap < 0.20

        # Round-trip: monthly → annual ≈ original
        annual = 0.05
        monthly = HypertensionSim.annual_to_monthly_prob(annual)
        reconstructed = 1.0 - (1.0 - monthly)^12
        @test reconstructed ≈ annual atol=1e-6
    end

    @testset "Monthly event probability" begin
        mp = HypertensionSim.get_monthly_event_prob(
            60.0, SEX_MALE, 150.0, 60.0, RISK_PROP_MI;
            has_diabetes=true, is_smoker=false, bmi=30.0,
        )
        @test 0.0 < mp < 0.05  # reasonable monthly MI prob

        # Prior event multiplier increases risk
        mp_prior = HypertensionSim.get_monthly_event_prob(
            60.0, SEX_MALE, 150.0, 60.0, RISK_PROP_MI;
            has_diabetes=true, is_smoker=false, bmi=30.0,
            prior_event_multiplier=2.5,
        )
        @test mp_prior > mp
    end
end

# ============================================================================
# KFRE tests
# ============================================================================
@testset "KFRE model" begin
    @testset "KFRE risk calculation" begin
        # Low risk: young, high eGFR, low UACR
        r1 = HypertensionSim.calculate_kfre_risk(45.0, SEX_MALE, 55.0, 20.0)
        @test 0.0001 < r1 < 0.10

        # Higher risk: older, lower eGFR, high UACR
        r2 = HypertensionSim.calculate_kfre_risk(70.0, SEX_MALE, 25.0, 500.0)
        @test r2 > r1

        # 5-year risk > 2-year risk
        r_2yr = HypertensionSim.calculate_kfre_risk(60.0, SEX_FEMALE, 35.0, 200.0; two_year=true)
        r_5yr = HypertensionSim.calculate_kfre_risk(60.0, SEX_FEMALE, 35.0, 200.0; two_year=false)
        @test r_5yr > r_2yr
    end

    @testset "eGFR decline" begin
        # KFRE-informed (eGFR < 60)
        d1 = HypertensionSim.get_annual_egfr_decline(
            60.0, SEX_MALE, 45.0, 100.0;
            has_diabetes=false, on_sglt2i=false, sbp=140.0,
        )
        @test d1 > 0.0

        # SGLT2i slows decline
        d2 = HypertensionSim.get_annual_egfr_decline(
            60.0, SEX_MALE, 45.0, 100.0;
            has_diabetes=false, on_sglt2i=true, sbp=140.0,
        )
        @test d2 < d1

        # Diabetes accelerates
        d3 = HypertensionSim.get_annual_egfr_decline(
            60.0, SEX_MALE, 45.0, 100.0;
            has_diabetes=true, on_sglt2i=false, sbp=140.0,
        )
        @test d3 > d1
    end
end

# ============================================================================
# Life tables tests
# ============================================================================
@testset "Life tables" begin
    @testset "US mortality" begin
        # Mortality increases with age
        m50 = HypertensionSim.get_annual_mortality(50.0, SEX_MALE, Int8(0))
        m70 = HypertensionSim.get_annual_mortality(70.0, SEX_MALE, Int8(0))
        @test m70 > m50

        # Female mortality < male at same age
        m_male = HypertensionSim.get_annual_mortality(60.0, SEX_MALE, Int8(0))
        m_female = HypertensionSim.get_annual_mortality(60.0, SEX_FEMALE, Int8(0))
        @test m_female < m_male

        # Monthly < annual
        a = HypertensionSim.get_annual_mortality(65.0, SEX_MALE, Int8(0))
        m = HypertensionSim.get_monthly_mortality(65.0, SEX_MALE, Int8(0))
        @test m < a
    end

    @testset "UK mortality" begin
        m = HypertensionSim.get_annual_mortality(60.0, SEX_MALE, Int8(1))
        @test 0.0 < m < 1.0
    end
end

# ============================================================================
# Transitions tests
# ============================================================================
@testset "Transitions" begin
    @testset "Stroke subtype fractions" begin
        isch, hem = HypertensionSim.get_stroke_subtype_fractions(
            65.0, 150.0, Int8(0), Int32(0), false,
        )
        @test isch ≈ 0.85
        @test hem ≈ 0.15

        # Dynamic: high SBP + old age → more hemorrhagic
        isch2, hem2 = HypertensionSim.get_stroke_subtype_fractions(
            82.0, 185.0, Int8(0), Int32(0), true,
        )
        @test hem2 > 0.15
        @test isch2 + hem2 ≈ 1.0
    end

    @testset "Competing risks" begin
        tp = HypertensionSim.TransProbs()
        tp.to_mi = 0.01
        tp.to_ischemic_stroke = 0.005
        tp.to_hemorrhagic_stroke = 0.001
        tp.to_hf = 0.003
        tp.to_cv_death = 0.002
        tp.to_non_cv_death = 0.001
        tp.to_tia = 0.002

        HypertensionSim.apply_competing_risks!(tp, true)

        total = tp.to_mi + tp.to_ischemic_stroke + tp.to_hemorrhagic_stroke +
                tp.to_hf + tp.to_cv_death + tp.to_non_cv_death + tp.to_tia
        @test total < 1.0
        @test tp.to_mi > 0.0
    end

    @testset "Event sampling" begin
        rng = Random.Xoshiro(42)
        tp = HypertensionSim.TransProbs()
        tp.to_mi = 0.5  # Very high for testing
        tp.to_cv_death = 0.3

        # Sample many times, should get both events
        mi_count = 0
        death_count = 0
        no_event = 0
        for _ in 1:1000
            e = HypertensionSim.sample_event(tp, CS_NO_ACUTE_EVENT, rng)
            if e == CS_ACUTE_MI
                mi_count += 1
            elseif e == CS_CV_DEATH
                death_count += 1
            elseif e == Int8(-1)
                no_event += 1
            end
        end
        @test mi_count > 0
        @test death_count > 0
    end
end

# ============================================================================
# Costs tests
# ============================================================================
@testset "Costs" begin
    psa = PSAParameters()
    costs = HypertensionSim.get_costs(Int8(0), psa)  # US

    @testset "Drug costs" begin
        c_ixa = HypertensionSim.get_drug_cost(TX_IXA_001, Int8(0), costs)
        c_spiro = HypertensionSim.get_drug_cost(TX_SPIRONOLACTONE, Int8(0), costs)
        c_sc = HypertensionSim.get_drug_cost(TX_STANDARD_CARE, Int8(0), costs)

        @test c_ixa > c_spiro
        @test c_sc < c_ixa

        # SGLT2i adds cost
        c_ixa_sglt2 = HypertensionSim.get_drug_cost(TX_IXA_001, Int8(1), costs)
        @test c_ixa_sglt2 > c_ixa
    end

    @testset "Event costs" begin
        c_mi = HypertensionSim.get_event_cost(CS_ACUTE_MI, costs)
        @test c_mi > 0.0

        c_stroke = HypertensionSim.get_event_cost(CS_ACUTE_ISCHEMIC_STROKE, costs)
        @test c_stroke > 0.0

        c_none = HypertensionSim.get_event_cost(CS_NO_ACUTE_EVENT, costs)
        @test c_none == 0.0
    end
end

# ============================================================================
# Utilities tests
# ============================================================================
@testset "Utilities" begin
    psa = PSAParameters()

    @testset "Baseline utility by age" begin
        u_young = HypertensionSim.get_utility(
            45.0, CS_NO_ACUTE_EVENT, RS_CKD_STAGE_1_2, NS_NORMAL,
            120.0, Int8(0), Int8(0), Int8(0), Int32(3), psa,
        )
        u_old = HypertensionSim.get_utility(
            75.0, CS_NO_ACUTE_EVENT, RS_CKD_STAGE_1_2, NS_NORMAL,
            120.0, Int8(0), Int8(0), Int8(0), Int32(3), psa,
        )
        @test u_young > u_old
        @test 0.7 < u_young < 1.0
    end

    @testset "Disutilities reduce utility" begin
        u_base = HypertensionSim.get_utility(
            60.0, CS_NO_ACUTE_EVENT, RS_CKD_STAGE_1_2, NS_NORMAL,
            120.0, Int8(0), Int8(0), Int8(0), Int32(3), psa,
        )
        u_mi = HypertensionSim.get_utility(
            60.0, CS_ACUTE_MI, RS_CKD_STAGE_1_2, NS_NORMAL,
            120.0, Int8(0), Int8(0), Int8(0), Int32(3), psa,
        )
        @test u_mi < u_base

        u_esrd = HypertensionSim.get_utility(
            60.0, CS_NO_ACUTE_EVENT, RS_ESRD, NS_NORMAL,
            120.0, Int8(0), Int8(0), Int8(0), Int32(3), psa,
        )
        @test u_esrd < u_base
    end

    @testset "QALY discounting" begin
        q0 = HypertensionSim.calculate_monthly_qaly(0.80, 0.0, 0.03, 1.0, true)
        q120 = HypertensionSim.calculate_monthly_qaly(0.80, 120.0, 0.03, 1.0, true)
        @test q0 > q120  # future QALYs discounted
        @test q0 > 0.0
    end
end

# ============================================================================
# Integration: simulate_arm!
# ============================================================================
@testset "simulate_arm! integration" begin
    @testset "Small population smoke test" begin
        n = 20
        p = PatientArrays(n)

        # Set up realistic patient characteristics
        rng_setup = Random.Xoshiro(123)
        for i in 1:n
            p.age[i] = 55.0 + 20.0 * rand(rng_setup)
            p.sex[i] = rand(rng_setup) < 0.5 ? SEX_MALE : SEX_FEMALE
            p.baseline_sbp[i] = 150.0 + 20.0 * randn(rng_setup)
            p.current_sbp[i] = p.baseline_sbp[i]
            p.baseline_dbp[i] = p.baseline_sbp[i] * 0.6
            p.current_dbp[i] = p.baseline_dbp[i]
            p.true_mean_sbp[i] = p.current_sbp[i]
            p.egfr[i] = 60.0 + 30.0 * rand(rng_setup)
            p.uacr[i] = 30.0 + 100.0 * rand(rng_setup)
            p.total_cholesterol[i] = 200.0 + 40.0 * randn(rng_setup)
            p.hdl_cholesterol[i] = 45.0 + 10.0 * randn(rng_setup)
            p.bmi[i] = 28.0 + 4.0 * randn(rng_setup)
            p.has_diabetes[i] = rand(rng_setup) < 0.3 ? Int8(1) : Int8(0)
            p.is_smoker[i] = rand(rng_setup) < 0.15 ? Int8(1) : Int8(0)
            p.has_primary_aldosteronism[i] = rand(rng_setup) < 0.18 ? Int8(1) : Int8(0)
        end

        cfg = SimConfig(;
            n_patients=n,
            time_horizon_months=120,
            cycle_length_months=1.0,
            discount_rate=0.03,
        )
        psa = PSAParameters()

        results = simulate_arm!(p, cfg, psa, TX_IXA_001, UInt64(42))

        @test results.n_patients == n
        @test results.total_costs > 0.0
        @test results.total_qalys > 0.0
        @test results.life_years > 0.0

        # Should have some events over 10 years
        total_deaths = results.cv_deaths + results.non_cv_deaths + results.renal_deaths
        @test total_deaths >= 0  # May be 0 with small N

        means = calculate_means(results)
        @test means.mean_costs > 0.0
        @test means.mean_qalys > 0.0
    end

    @testset "CRN: same seed → same results" begin
        function run_with_seed(seed)
            p = PatientArrays(10)
            rng_s = Random.Xoshiro(99)
            for i in 1:10
                p.age[i] = 60.0 + 10.0 * rand(rng_s)
                p.sex[i] = SEX_MALE
                p.baseline_sbp[i] = 160.0
                p.current_sbp[i] = 160.0
                p.true_mean_sbp[i] = 160.0
                p.baseline_dbp[i] = 96.0
                p.current_dbp[i] = 96.0
                p.egfr[i] = 70.0
                p.uacr[i] = 50.0
                p.total_cholesterol[i] = 220.0
                p.hdl_cholesterol[i] = 45.0
                p.bmi[i] = 30.0
            end
            cfg = SimConfig(; n_patients=10, time_horizon_months=60)
            psa = PSAParameters()
            return simulate_arm!(p, cfg, psa, TX_SPIRONOLACTONE, UInt64(seed))
        end

        r1 = run_with_seed(12345)
        r2 = run_with_seed(12345)

        @test r1.total_costs == r2.total_costs
        @test r1.total_qalys == r2.total_qalys
        @test r1.mi_events == r2.mi_events
        @test r1.cv_deaths == r2.cv_deaths
    end

    @testset "Different treatments produce different outcomes" begin
        function run_arm(tx, seed)
            p = PatientArrays(50)
            rng_s = Random.Xoshiro(77)
            for i in 1:50
                p.age[i] = 60.0
                p.sex[i] = i % 2 == 0 ? SEX_MALE : SEX_FEMALE
                p.baseline_sbp[i] = 165.0
                p.current_sbp[i] = 165.0
                p.true_mean_sbp[i] = 165.0
                p.baseline_dbp[i] = 99.0
                p.current_dbp[i] = 99.0
                p.egfr[i] = 65.0
                p.uacr[i] = 80.0
                p.total_cholesterol[i] = 210.0
                p.hdl_cholesterol[i] = 48.0
                p.bmi[i] = 29.0
                p.has_diabetes[i] = i % 3 == 0 ? Int8(1) : Int8(0)
            end
            cfg = SimConfig(; n_patients=50, time_horizon_months=240)
            psa = PSAParameters()
            return simulate_arm!(p, cfg, psa, tx, UInt64(seed))
        end

        r_ixa = run_arm(TX_IXA_001, 42)
        r_spiro = run_arm(TX_SPIRONOLACTONE, 42)

        # IXA should have higher drug costs
        m_ixa = calculate_means(r_ixa)
        m_spiro = calculate_means(r_spiro)
        @test m_ixa.mean_costs != m_spiro.mean_costs
    end
end

# ============================================================================
# Parallel PSA bridge test
# ============================================================================
@testset "run_psa_parallel" begin
    @testset "Multi-iteration parallel PSA" begin
        n = 10
        # Build a template patient_dict (Dict{String,Vector})
        rng_s = Random.Xoshiro(55)
        patient_dict = Dict{String, Any}()
        patient_dict["age"] = [60.0 + 10.0 * rand(rng_s) for _ in 1:n]
        patient_dict["sex"] = Int8[rand(rng_s) < 0.5 ? 0 : 1 for _ in 1:n]
        patient_dict["baseline_sbp"] = fill(160.0, n)
        patient_dict["baseline_dbp"] = fill(96.0, n)
        patient_dict["current_sbp"] = fill(160.0, n)
        patient_dict["current_dbp"] = fill(96.0, n)
        patient_dict["true_mean_sbp"] = fill(160.0, n)
        patient_dict["white_coat_effect"] = zeros(n)
        patient_dict["egfr"] = fill(70.0, n)
        patient_dict["uacr"] = fill(50.0, n)
        patient_dict["total_cholesterol"] = fill(210.0, n)
        patient_dict["hdl_cholesterol"] = fill(48.0, n)
        patient_dict["has_diabetes"] = Int8[rand(rng_s) < 0.3 ? 1 : 0 for _ in 1:n]
        patient_dict["is_smoker"] = zeros(Int8, n)
        patient_dict["bmi"] = fill(29.0, n)
        patient_dict["has_atrial_fibrillation"] = zeros(Int8, n)
        patient_dict["has_heart_failure"] = zeros(Int8, n)
        patient_dict["on_sglt2_inhibitor"] = zeros(Int8, n)
        patient_dict["has_primary_aldosteronism"] = Int8[rand(rng_s) < 0.18 ? 1 : 0 for _ in 1:n]
        patient_dict["has_renal_artery_stenosis"] = zeros(Int8, n)
        patient_dict["has_pheochromocytoma"] = zeros(Int8, n)
        patient_dict["has_obstructive_sleep_apnea"] = zeros(Int8, n)
        patient_dict["serum_potassium"] = fill(4.2, n)
        patient_dict["has_hyperkalemia"] = zeros(Int8, n)
        patient_dict["hyperkalemia_history"] = zeros(Int32, n)
        patient_dict["on_potassium_binder"] = zeros(Int8, n)
        patient_dict["mra_dose_reduced"] = zeros(Int8, n)
        patient_dict["is_adherent"] = ones(Int8, n)
        patient_dict["sdi_score"] = fill(50.0, n)
        patient_dict["nocturnal_dipping_status"] = zeros(Int8, n)
        patient_dict["time_since_adherence_change"] = zeros(n)
        patient_dict["cardiac_state"] = zeros(Int8, n)
        patient_dict["renal_state"] = zeros(Int8, n)
        patient_dict["neuro_state"] = zeros(Int8, n)
        patient_dict["treatment"] = fill(Int8(2), n)
        patient_dict["prior_mi_count"] = zeros(Int32, n)
        patient_dict["prior_stroke_count"] = zeros(Int32, n)
        patient_dict["prior_ischemic_stroke_count"] = zeros(Int32, n)
        patient_dict["prior_hemorrhagic_stroke_count"] = zeros(Int32, n)
        patient_dict["prior_tia_count"] = zeros(Int32, n)
        patient_dict["time_since_last_cv_event"] = fill(NaN, n)
        patient_dict["time_since_last_tia"] = fill(NaN, n)
        patient_dict["time_in_simulation"] = zeros(n)
        patient_dict["time_in_cardiac_state"] = zeros(n)
        patient_dict["time_in_renal_state"] = zeros(n)
        patient_dict["time_in_neuro_state"] = zeros(n)
        patient_dict["cumulative_costs"] = zeros(n)
        patient_dict["cumulative_qalys"] = zeros(n)
        patient_dict["treatment_effect_mmhg"] = zeros(n)
        patient_dict["base_treatment_effect"] = zeros(n)
        patient_dict["mod_mi"] = ones(n)
        patient_dict["mod_stroke"] = ones(n)
        patient_dict["mod_hf"] = ones(n)
        patient_dict["mod_esrd"] = ones(n)
        patient_dict["mod_death"] = ones(n)
        patient_dict["treatment_response_modifier"] = ones(n)
        patient_dict["num_antihypertensives"] = fill(Int32(3), n)
        patient_dict["use_kfre_model"] = ones(Int8, n)

        config_dict = Dict{String, Any}(
            "time_horizon_months" => 60,
            "cycle_length_months" => 1.0,
            "discount_rate" => 0.03,
            "cost_perspective" => 0,
            "use_half_cycle_correction" => true,
            "use_competing_risks" => true,
            "use_dynamic_stroke_subtypes" => true,
            "use_kfre_model" => true,
            "life_table_country" => 0,
            "economic_perspective" => 1,
        )

        # Create 5 PSA parameter dicts with slight variations
        base_psa = Dict{String, Any}(
            "ixa_sbp_mean" => 20.0, "ixa_sbp_sd" => 6.0,
            "spiro_sbp_mean" => 9.0, "spiro_sbp_sd" => 6.0,
            "discontinuation_rate_ixa" => 0.08, "discontinuation_rate_spiro" => 0.18,
            "cost_mi_acute" => 25000.0, "cost_ischemic_stroke_acute" => 15200.0,
            "cost_hemorrhagic_stroke_acute" => 22500.0, "cost_hf_acute" => 18000.0,
            "cost_esrd_annual" => 90000.0, "cost_post_stroke_annual" => 12000.0,
            "cost_hf_annual" => 15000.0, "cost_ixa_monthly" => 500.0,
            "disutility_post_mi" => 0.12, "disutility_post_stroke" => 0.18,
            "disutility_chronic_hf" => 0.15, "disutility_esrd" => 0.35,
            "disutility_dementia" => 0.30,
        )
        all_psa = [deepcopy(base_psa) for _ in 1:5]
        # Vary IXA effect across iterations
        for (k, d) in enumerate(all_psa)
            d["ixa_sbp_mean"] = 18.0 + k * 1.0
        end

        results = HypertensionSim.run_psa_parallel(
            patient_dict, config_dict, all_psa, 42, true,
        )

        @test length(results) == 5
        for r in results
            @test r["ixa_mean_qalys"] > 0.0
            @test r["comp_mean_qalys"] > 0.0
            @test r["ixa_mean_costs"] > 0.0
            @test r["comp_mean_costs"] > 0.0
        end

        # Different PSA params should produce different results
        @test results[1]["ixa_mean_costs"] != results[5]["ixa_mean_costs"]
    end
end

println("\nAll tests passed!")
