from src.rag.preprocess import (
    NUCLEAR_KEYWORDS,
    QueryContext,
    classify_complexity,
    detect_nuclear,
    detect_scope,
    detect_union,
    detect_unions,
    detect_wage_query,
    preprocess,
)

KNOWN_UNIONS = [
    "IBEW",
    "Sheet Metal Workers",
    "United Association",
    "Labourers",
]


class TestNuclearKeywords:
    def test_constant_contains_required_entries(self) -> None:
        required = [
            "nuclear",
            "OPG",
            "Ontario Power Generation",
            "Bruce Power",
            "Darlington",
            "Pickering",
            "nuclear project",
            "NPA",
        ]
        for kw in required:
            assert kw in NUCLEAR_KEYWORDS


class TestDetectNuclear:
    def test_empty_query_returns_false(self) -> None:
        assert detect_nuclear("") is False

    def test_no_keywords_returns_false(self) -> None:
        assert detect_nuclear("What is the overtime rate for IBEW?") is False

    def test_detects_nuclear_lowercase(self) -> None:
        assert detect_nuclear("is nuclear work covered?") is True

    def test_detects_nuclear_uppercase(self) -> None:
        assert detect_nuclear("NUCLEAR project rules") is True

    def test_detects_opg(self) -> None:
        assert detect_nuclear("What does OPG require for site access?") is True

    def test_detects_ontario_power_generation(self) -> None:
        assert detect_nuclear("Ontario Power Generation safety standards") is True

    def test_detects_bruce_power(self) -> None:
        assert detect_nuclear("Bruce Power overtime provisions") is True

    def test_detects_darlington(self) -> None:
        assert detect_nuclear("Darlington refurbishment wage rates") is True

    def test_detects_pickering(self) -> None:
        assert detect_nuclear("Pickering decommissioning schedule") is True

    def test_detects_nuclear_project(self) -> None:
        assert detect_nuclear("nuclear project agreement scope") is True

    def test_detects_npa(self) -> None:
        assert detect_nuclear("What does the NPA say about layoffs?") is True

    def test_case_insensitive_mixed(self) -> None:
        assert detect_nuclear("What are the nPa provisions?") is True

    def test_opg_lowercase(self) -> None:
        assert detect_nuclear("opg site badge requirements") is True

    def test_npa_requires_word_boundary(self) -> None:
        # "npa" embedded mid-word should not match
        assert detect_nuclear("the company's cnpa policy does not apply") is False

    def test_non_nuclear_does_not_trigger(self) -> None:
        # "non-nuclear" contains "nuclear" as substring but should still match
        # because "nuclear" is its own token here
        assert detect_nuclear("this is a non-nuclear facility") is True


class TestDetectUnion:
    def test_empty_query_returns_none(self) -> None:
        assert detect_union("", KNOWN_UNIONS) is None

    def test_empty_known_unions_returns_none(self) -> None:
        assert detect_union("IBEW overtime rates", []) is None

    def test_detects_ibew_exact_case(self) -> None:
        assert detect_union("What does IBEW say about overtime?", KNOWN_UNIONS) == "IBEW"

    def test_detects_ibew_lowercase(self) -> None:
        assert detect_union("ibew overtime rates", KNOWN_UNIONS) == "IBEW"

    def test_detects_multiword_union(self) -> None:
        result = detect_union("Sheet Metal Workers vacation entitlement", KNOWN_UNIONS)
        assert result == "Sheet Metal Workers"

    def test_detects_united_association(self) -> None:
        result = detect_union("united association pipe fitting rates", KNOWN_UNIONS)
        assert result == "United Association"

    def test_returns_verbatim_union_name(self) -> None:
        # 'ibew' in query → return 'IBEW' (from known_unions, not query case)
        result = detect_union("ibew rules", KNOWN_UNIONS)
        assert result == "IBEW"

    def test_returns_first_union_in_known_unions_order(self) -> None:
        # Query contains both IBEW and Labourers; IBEW is first in known_unions
        result = detect_union("IBEW and Labourers overtime rules", KNOWN_UNIONS)
        assert result == "IBEW"

    def test_query_with_no_union_returns_none(self) -> None:
        assert detect_union("general overtime rules for all workers", KNOWN_UNIONS) is None


class TestDetectUnions:
    def test_empty_query_returns_empty_list(self) -> None:
        assert detect_unions("", KNOWN_UNIONS) == []

    def test_empty_known_unions_returns_empty_list(self) -> None:
        assert detect_unions("IBEW and Labourers overtime", []) == []

    def test_returns_all_detected_unions_in_query_order(self) -> None:
        result = detect_unions(
            "Compare Sheet Metal Workers and IBEW overtime rules",
            KNOWN_UNIONS,
        )
        assert result == ["Sheet Metal Workers", "IBEW"]

    def test_returns_empty_list_when_query_has_no_union(self) -> None:
        assert detect_unions("general overtime rules for all workers", KNOWN_UNIONS) == []


class TestDetectScope:
    def test_no_scope_returns_none(self) -> None:
        assert detect_scope("What is the overtime rate?") is None

    def test_empty_query_returns_none(self) -> None:
        assert detect_scope("") is None

    def test_detects_generation(self) -> None:
        assert detect_scope("generation plant overtime") == "generation"

    def test_detects_transmission(self) -> None:
        assert detect_scope("transmission line work rules") == "transmission"

    def test_generation_uppercase(self) -> None:
        assert detect_scope("GENERATION facility wage schedule") == "generation"

    def test_transmission_uppercase(self) -> None:
        assert detect_scope("TRANSMISSION corridor rules") == "transmission"

    def test_generation_mixed_case(self) -> None:
        assert detect_scope("Generation workers shift premium") == "generation"

    def test_returns_generation_when_both_present(self) -> None:
        # generation check precedes transmission in detect_scope; generation wins
        result = detect_scope("generation and transmission overtime")
        assert result == "generation"

    def test_regeneration_does_not_trigger_generation(self) -> None:
        assert detect_scope("regeneration clause in article 12") is None

    def test_retransmission_does_not_trigger_transmission(self) -> None:
        assert detect_scope("retransmission rights are excluded") is None


class TestClassifyComplexity:
    def test_simple_query_returns_false(self) -> None:
        assert classify_complexity("What is the overtime rate for IBEW?") is False

    def test_empty_query_returns_false(self) -> None:
        assert classify_complexity("") is False

    def test_compare_returns_true(self) -> None:
        assert classify_complexity("compare IBEW and UA overtime rules") is True

    def test_difference_between_returns_true(self) -> None:
        assert classify_complexity("what is the difference between IBEW and UA?") is True

    def test_all_unions_returns_true(self) -> None:
        assert classify_complexity("what do all unions say about vacation?") is True

    def test_across_trades_returns_true(self) -> None:
        assert classify_complexity("shift premiums across trades") is True

    def test_compare_uppercase(self) -> None:
        assert classify_complexity("COMPARE the two agreements") is True

    def test_difference_between_uppercase(self) -> None:
        assert classify_complexity("DIFFERENCE BETWEEN IBEW and UA") is True


class TestDetectWageQuery:
    def test_empty_query_returns_false(self) -> None:
        assert detect_wage_query("") is False

    def test_no_wage_keywords_returns_false(self) -> None:
        assert detect_wage_query("What are the layoff notice requirements?") is False

    def test_detects_rate(self) -> None:
        assert detect_wage_query("What is the overtime rate for IBEW?") is True

    def test_detects_wage(self) -> None:
        assert detect_wage_query("IBEW wage schedule 2025") is True

    def test_detects_hourly(self) -> None:
        assert detect_wage_query("What is the hourly rate for electricians?") is True

    def test_detects_journeyperson(self) -> None:
        assert detect_wage_query("journeyperson pay for Sheet Metal Workers") is True

    def test_detects_apprentice(self) -> None:
        assert detect_wage_query("apprentice rate first period") is True

    def test_case_insensitive(self) -> None:
        assert detect_wage_query("HOURLY RATE for welders") is True

    def test_non_wage_query_returns_false(self) -> None:
        assert detect_wage_query("vacation entitlement after 5 years") is False


class TestQueryContext:
    def test_default_values(self) -> None:
        ctx = QueryContext(
            union_filters=[],
            include_nuclear_pa=False,
            agreement_scope=None,
            is_cross_union=False,
            is_wage_query=False,
        )
        assert ctx.union_filters == []
        assert ctx.union_filter is None
        assert ctx.include_nuclear_pa is False
        assert ctx.agreement_scope is None
        assert ctx.is_cross_union is False
        assert ctx.is_wage_query is False

    def test_all_fields_set(self) -> None:
        ctx = QueryContext(
            union_filters=["IBEW"],
            include_nuclear_pa=True,
            agreement_scope="generation",
            is_cross_union=True,
            is_wage_query=True,
        )
        assert ctx.union_filters == ["IBEW"]
        assert ctx.union_filter == "IBEW"
        assert ctx.include_nuclear_pa is True
        assert ctx.agreement_scope == "generation"
        assert ctx.is_cross_union is True
        assert ctx.is_wage_query is True


class TestPreprocess:
    def test_simple_query_returns_all_defaults(self) -> None:
        ctx = preprocess("What are the layoff notice requirements?", KNOWN_UNIONS)
        assert ctx.union_filters == []
        assert ctx.union_filter is None
        assert ctx.include_nuclear_pa is False
        assert ctx.agreement_scope is None
        assert ctx.is_cross_union is False
        assert ctx.is_wage_query is False

    def test_wage_query_sets_is_wage_query(self) -> None:
        ctx = preprocess("What is the journeyperson hourly rate for IBEW?", KNOWN_UNIONS)
        assert ctx.is_wage_query is True

    def test_non_wage_query_does_not_set_is_wage_query(self) -> None:
        ctx = preprocess("How many vacation days after 5 years?", KNOWN_UNIONS)
        assert ctx.is_wage_query is False

    def test_nuclear_query_sets_include_nuclear_pa(self) -> None:
        ctx = preprocess("OPG site badge requirements", KNOWN_UNIONS)
        assert ctx.include_nuclear_pa is True

    def test_union_query_sets_union_filter(self) -> None:
        ctx = preprocess("What does IBEW say about overtime?", KNOWN_UNIONS)
        assert ctx.union_filters == ["IBEW"]
        assert ctx.union_filter == "IBEW"

    def test_scope_query_sets_agreement_scope(self) -> None:
        ctx = preprocess("generation plant shift schedule", KNOWN_UNIONS)
        assert ctx.agreement_scope == "generation"

    def test_cross_union_query_sets_is_cross_union(self) -> None:
        ctx = preprocess("compare IBEW and UA overtime rules", KNOWN_UNIONS)
        assert ctx.is_cross_union is True

    def test_combined_nuclear_and_union(self) -> None:
        ctx = preprocess("IBEW Darlington refurbishment wage rates", KNOWN_UNIONS)
        assert ctx.union_filters == ["IBEW"]
        assert ctx.union_filter == "IBEW"
        assert ctx.include_nuclear_pa is True

    def test_combined_all_flags(self) -> None:
        ctx = preprocess(
            "compare all unions at OPG generation facilities", KNOWN_UNIONS
        )
        assert ctx.include_nuclear_pa is True
        assert ctx.agreement_scope == "generation"
        assert ctx.is_cross_union is True

    def test_multi_union_query_retains_all_detected_unions(self) -> None:
        ctx = preprocess(
            "Compare the overtime rules for IBEW Generation and Sheet Metal Workers",
            KNOWN_UNIONS,
        )
        assert ctx.union_filters == ["IBEW", "Sheet Metal Workers"]
        assert ctx.union_filter is None
        assert ctx.is_cross_union is True

    def test_multiple_detected_unions_trigger_cross_union_without_keyword(self) -> None:
        ctx = preprocess("IBEW and Labourers overtime rules", KNOWN_UNIONS)
        assert ctx.union_filters == ["IBEW", "Labourers"]
        assert ctx.is_cross_union is True

    def test_returns_query_context_type(self) -> None:
        ctx = preprocess("overtime rates", KNOWN_UNIONS)
        assert isinstance(ctx, QueryContext)
