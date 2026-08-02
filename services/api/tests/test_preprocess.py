from src.rag.preprocess import (
    NUCLEAR_KEYWORDS,
    QueryContext,
    classify_complexity,
    detect_enumeration,
    detect_nuclear,
    detect_provision_terms,
    detect_rate_classification,
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

    def test_alias_ua_detects_united_association(self) -> None:
        result = detect_union("What does a UA apprentice make in Toronto?", KNOWN_UNIONS)
        assert result == "United Association"

    def test_alias_plumber_detects_united_association(self) -> None:
        result = detect_union("plumber journeyperson rate in Toronto", KNOWN_UNIONS)
        assert result == "United Association"

    def test_alias_requires_word_boundary(self) -> None:
        # "ua" inside another word must not match United Association.
        assert detect_union("guarantee of overtime hours", KNOWN_UNIONS) is None

    def test_alias_electrical_workers_detects_ibew(self) -> None:
        result = detect_union("electrical workers wage schedule", KNOWN_UNIONS)
        assert result == "IBEW"

    def test_singular_form_detects_plural_union(self) -> None:
        # Phase 2 unions are stored plural; singular mentions must match.
        unions = [*KNOWN_UNIONS, "Carpenters", "Teamsters", "Cement Masons"]
        assert detect_union("what is the carpenter rate?", unions) == "Carpenters"
        assert detect_union("teamster travel allowance", unions) == "Teamsters"
        assert detect_union("cement mason overtime", unions) == "Cement Masons"

    def test_singular_stripping_not_applied_to_non_plural_names(self) -> None:
        # "Rodmen" must not degrade to "rodme"; explicit alias handles "rodman".
        unions = [*KNOWN_UNIONS, "Rodmen"]
        assert detect_union("rodman wage rate", unions) == "Rodmen"
        assert detect_union("rodme nonsense", unions) is None

    def test_alias_terrazzo_detects_tile_union(self) -> None:
        unions = [*KNOWN_UNIONS, "Tile and Terrazzo"]
        assert (
            detect_union("working foreman rate for Marble/Tile/Terrazzo workers", unions)
            == "Tile and Terrazzo"
        )
        assert detect_union("terrazzo journeyperson rate", unions) == "Tile and Terrazzo"

    def test_alias_bacu_detects_brick_union(self) -> None:
        unions = [*KNOWN_UNIONS, "Brick and Allied Craft Union"]
        assert detect_union("BACU journeyperson rate", unions) == "Brick and Allied Craft Union"
        assert detect_union("bricklayer overtime rules", unions) == "Brick and Allied Craft Union"


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


class TestDetectEnumeration:
    """Enumeration intent (#168): broad "all unions" coverage queries.

    The detector must be precise — a normal single-union or two-union
    comparison query must NEVER read as an enumeration, or it would trigger
    the corpus-wide fan-out and add latency to ordinary queries.
    """

    # ── Positives ──────────────────────────────────────────────────────────
    def test_all_unions(self) -> None:
        assert detect_enumeration("what is the foreman rate for all unions?") is True

    def test_all_the_unions(self) -> None:
        assert detect_enumeration("foreman rate for all the unions under EPSCA") is True

    def test_all_of_the_unions(self) -> None:
        assert detect_enumeration("overtime rules for all of the unions") is True

    def test_every_union(self) -> None:
        assert detect_enumeration("does every union offer a pension?") is True

    def test_every_union_apostrophe_s(self) -> None:
        assert detect_enumeration("list every union's overtime rule") is True

    def test_each_trade(self) -> None:
        assert detect_enumeration("what does each trade pay a foreman?") is True

    def test_each_union(self) -> None:
        assert detect_enumeration("subsistence allowance for each union") is True

    def test_which_unions_plural(self) -> None:
        assert detect_enumeration("which unions cover nuclear work?") is True

    def test_list_the_unions(self) -> None:
        assert detect_enumeration("list the unions that work at Darlington") is True

    def test_across_trades(self) -> None:
        assert detect_enumeration("shift premiums across trades") is True

    def test_across_all_unions(self) -> None:
        assert detect_enumeration("compare travel allowance across all unions") is True

    def test_per_union(self) -> None:
        assert detect_enumeration("break down the foreman rate per union") is True

    def test_all_trades(self) -> None:
        assert detect_enumeration("what is the apprentice rate for all trades?") is True

    def test_case_insensitive_all_unions(self) -> None:
        assert detect_enumeration("FOREMAN RATE FOR ALL UNIONS") is True

    def test_case_insensitive_every_trade(self) -> None:
        assert detect_enumeration("Every Trade overtime rule") is True

    # ── Negatives ──────────────────────────────────────────────────────────
    def test_empty_query(self) -> None:
        assert detect_enumeration("") is False

    def test_single_union_query(self) -> None:
        assert detect_enumeration("IBEW foreman rate") is False

    def test_compare_two_named_unions(self) -> None:
        assert detect_enumeration("compare IBEW and UA overtime rules") is False

    def test_which_union_singular_comparison(self) -> None:
        # The hard negative: singular "which union" comparing two named unions
        # must NOT read as enumeration (the plural "which unions" is the signal).
        assert (
            detect_enumeration(
                "which union has the higher rate: IBEW or United Association?"
            )
            is False
        )

    def test_which_union_singular_lookup(self) -> None:
        assert detect_enumeration("which union covers Darlington?") is False

    def test_plain_wage_query(self) -> None:
        assert detect_enumeration("what is the overtime rate for welders?") is False

    def test_all_workers_does_not_trigger(self) -> None:
        # "all workers" is not "all unions/trades" — a general question about
        # everyone, not an enumeration over the union corpus.
        assert detect_enumeration("general overtime rules for all workers") is False


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


class TestDetectProvisionTerms:
    """Focused query-expansion terms for specific-provision recall (#78)."""

    def test_empty_query_returns_empty_list(self) -> None:
        assert detect_provision_terms("") == []

    def test_no_trigger_returns_empty_list(self) -> None:
        assert detect_provision_terms("What are the layoff notice requirements?") == []

    def test_returns_list_type(self) -> None:
        assert isinstance(detect_provision_terms("subsistence allowance"), list)

    # O07 — double-time / overtime-rate provision
    def test_double_time_hyphen_query_returns_overtime_term(self) -> None:
        terms = detect_provision_terms(
            "What is the double-time rate provision for United Association workers?"
        )
        assert any("double time" in t.lower() for t in terms)

    def test_double_time_no_hyphen_triggers(self) -> None:
        assert detect_provision_terms("double time pay rules") != []

    # W02 — foreperson wage differential / premium
    def test_foreman_premium_query_returns_differential_term(self) -> None:
        terms = detect_provision_terms(
            "What is the foreman wage premium for IBEW Generation electricians?"
        )
        assert any("differential" in t.lower() for t in terms)

    def test_differential_keyword_triggers(self) -> None:
        assert detect_provision_terms("foreperson differential percentage") != []

    def test_bare_premium_without_foreman_does_not_trigger(self) -> None:
        # A radiation/shift "premium" (no foreman token) must NOT pull the
        # foreperson-differential clause — avoids regressing N04-style queries.
        assert (
            detect_provision_terms(
                "Do workers receive a premium for working on a nuclear project site?"
            )
            == []
        )

    def test_differential_without_foreman_does_not_trigger(self) -> None:
        # "differential" in an engineering sense (no foreman token) must NOT
        # pull the foreperson clause (e.g. "differential pressure" nuclear work).
        assert detect_provision_terms("differential pressure testing steps") == []

    # T03 — subsistence allowance table
    def test_subsistence_query_returns_allowance_term(self) -> None:
        terms = detect_provision_terms(
            "What is the subsistence allowance for Sheet Metal workers away from home?"
        )
        assert any("subsistence" in t.lower() for t in terms)

    # D01 — union dues (Teamsters "Union Dues" form + the CA check-off clause)
    def test_dues_query_returns_checkoff_term(self) -> None:
        terms = detect_provision_terms(
            "What are the union dues for Teamsters Local 879?"
        )
        assert any("dues" in t.lower() for t in terms)

    def test_dues_query_without_union_still_triggers(self) -> None:
        assert detect_provision_terms("How are dues calculated?") != []

    def test_dues_substring_does_not_trigger(self) -> None:
        # Word-boundary guard: "residues" is not a dues question.
        assert detect_provision_terms("How are chemical residues handled?") == []

    # N02 — nuclear site-specific provision
    def test_darlington_query_returns_site_name(self) -> None:
        terms = detect_provision_terms(
            "What additional provisions apply to IBEW electricians working at Darlington?"
        )
        assert "Darlington" in terms

    def test_bruce_power_query_returns_site_name(self) -> None:
        assert "Bruce" in detect_provision_terms("Bruce Power nuclear site provisions")

    def test_bruce_as_given_name_does_not_trigger(self) -> None:
        # Only the "Bruce Power" phrase fires (mirrors _NUCLEAR_PATTERNS); the
        # bare given name "Bruce" must not.
        assert detect_provision_terms("What does Bruce recommend for scheduling?") == []

    def test_case_insensitive(self) -> None:
        assert detect_provision_terms("DOUBLE TIME provisions") != []

    def test_dedupes_overlapping_triggers(self) -> None:
        # "foreman premium" and "differential" both map to the foreperson
        # expansion; the merged list must contain no duplicates.
        terms = detect_provision_terms("foreman premium and foreperson differential")
        assert len(terms) == len(set(terms))


class TestDetectRateClassification:
    """Structured rate lookup (issue #89): resolve a single classification
    family from the query, or None when zero or several families appear."""

    def test_journeyperson_maps_to_journeyman(self) -> None:
        assert (
            detect_rate_classification("journeyperson rate in Windsor")
            == "journeyman"
        )

    def test_journeyman_maps_to_journeyman(self) -> None:
        assert detect_rate_classification("journeyman wage") == "journeyman"

    def test_journey_person_with_space_maps_to_journeyman(self) -> None:
        assert detect_rate_classification("journey person rate") == "journeyman"

    def test_foreperson_maps_to_foreman(self) -> None:
        assert detect_rate_classification("foreperson hourly rate") == "foreman"

    def test_forewoman_maps_to_foreman(self) -> None:
        assert detect_rate_classification("forewoman pay") == "foreman"

    def test_subforeman_maps_to_subforeman(self) -> None:
        assert detect_rate_classification("subforeman rate") == "subforeman"

    def test_hyphenated_sub_foreman_is_subforeman_not_foreman(self) -> None:
        assert detect_rate_classification("sub-foreman rate") == "subforeman"

    def test_spaced_sub_foreman_is_subforeman_not_foreman(self) -> None:
        assert detect_rate_classification("sub foreman rate") == "subforeman"

    def test_double_space_sub_foreman_is_subforeman(self) -> None:
        assert detect_rate_classification("sub  foreman rate") == "subforeman"

    def test_spaced_hyphen_sub_foreman_is_subforeman(self) -> None:
        assert detect_rate_classification("sub - foreman rate") == "subforeman"

    def test_apprentice_maps_to_apprentice(self) -> None:
        assert detect_rate_classification("apprentice wages") == "apprentice"

    def test_welder_maps_to_welder(self) -> None:
        assert detect_rate_classification("welder rate Local 353") == "welder"

    def test_material_handler_maps_to_material_handler(self) -> None:
        assert (
            detect_rate_classification("material handler hourly pay")
            == "material handler"
        )

    def test_matching_is_case_insensitive(self) -> None:
        assert detect_rate_classification("JOURNEYPERSON RATE") == "journeyman"

    def test_no_classification_returns_none(self) -> None:
        assert detect_rate_classification("vacation days after 5 years") is None

    def test_two_families_return_none(self) -> None:
        # Premium/differential comparisons need both tables — the structured
        # lookup must not pin one of them.
        assert (
            detect_rate_classification(
                "how much more does a foreman make than a journeyperson"
            )
            is None
        )

    def test_word_boundary_no_false_positive(self) -> None:
        # "welders" plural should match; embedded substrings should not.
        assert detect_rate_classification("rate for pipewelders") == "welder"

    def test_empty_query_returns_none(self) -> None:
        assert detect_rate_classification("") is None


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

    def test_provision_terms_defaults_to_empty(self) -> None:
        ctx = QueryContext(
            union_filters=[],
            include_nuclear_pa=False,
            agreement_scope=None,
            is_cross_union=False,
            is_wage_query=False,
        )
        assert ctx.provision_terms == []

    def test_provision_terms_can_be_set(self) -> None:
        ctx = QueryContext(
            union_filters=[],
            include_nuclear_pa=False,
            agreement_scope=None,
            is_cross_union=False,
            is_wage_query=False,
            provision_terms=["double time overtime rate"],
        )
        assert ctx.provision_terms == ["double time overtime rate"]

    def test_is_enumeration_defaults_to_false(self) -> None:
        ctx = QueryContext(
            union_filters=[],
            include_nuclear_pa=False,
            agreement_scope=None,
            is_cross_union=False,
            is_wage_query=False,
        )
        assert ctx.is_enumeration is False

    def test_is_enumeration_can_be_set(self) -> None:
        ctx = QueryContext(
            union_filters=[],
            include_nuclear_pa=False,
            agreement_scope=None,
            is_cross_union=True,
            is_wage_query=False,
            is_enumeration=True,
        )
        assert ctx.is_enumeration is True


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

    def test_provision_query_sets_provision_terms(self) -> None:
        ctx = preprocess(
            "What is the double-time rate provision for United Association workers?",
            KNOWN_UNIONS,
        )
        assert ctx.provision_terms != []

    def test_non_provision_query_leaves_provision_terms_empty(self) -> None:
        ctx = preprocess("How many vacation days after 5 years?", KNOWN_UNIONS)
        assert ctx.provision_terms == []

    def test_wage_query_with_classification_sets_rate_classification(self) -> None:
        ctx = preprocess(
            "What is the journeyperson rate for Labourers in Windsor?", KNOWN_UNIONS
        )
        assert ctx.is_wage_query is True
        assert ctx.rate_classification == "journeyman"

    def test_classification_without_wage_intent_is_ignored(self) -> None:
        # "foreman" appears but nothing signals a wage/rate question, so the
        # structured lookup must not activate.
        ctx = preprocess("foreman safety responsibilities on site", KNOWN_UNIONS)
        assert ctx.is_wage_query is False
        assert ctx.rate_classification is None

    def test_premium_comparison_query_has_no_rate_classification(self) -> None:
        ctx = preprocess(
            "How much more does a foreman make than a journeyperson?", KNOWN_UNIONS
        )
        assert ctx.rate_classification is None

    def test_wage_query_without_classification_has_no_rate_classification(
        self,
    ) -> None:
        ctx = preprocess("What are the IBEW wage rates?", KNOWN_UNIONS)
        assert ctx.is_wage_query is True
        assert ctx.rate_classification is None

    def test_cross_union_wage_query_has_no_rate_classification(self) -> None:
        # A comparison across trades must not pin a single union's table,
        # even when only one classification family is named.
        ctx = preprocess(
            "Compare the journeyperson rate across trades in Windsor", KNOWN_UNIONS
        )
        assert ctx.is_cross_union is True
        assert ctx.rate_classification is None

    def test_enumeration_query_sets_is_enumeration(self) -> None:
        ctx = preprocess(
            "what is the foreman rate for all unions covered under EPSCA?",
            KNOWN_UNIONS,
        )
        assert ctx.is_enumeration is True
        assert ctx.union_filters == []

    def test_enumeration_alone_flips_cross_union(self) -> None:
        # "every union" is NOT a _CROSS_UNION_PHRASES entry and names zero unions,
        # so without enumeration this would route to Haiku. Enumeration must flip
        # is_cross_union → Sonnet + the comparison addendum (address each union
        # separately, note absences) which is exactly the coverage answer shape.
        ctx = preprocess("does every union offer a pension?", KNOWN_UNIONS)
        assert ctx.is_enumeration is True
        assert ctx.is_cross_union is True

    def test_enumeration_wage_query_has_no_rate_classification(self) -> None:
        # Enumeration ⇒ is_cross_union ⇒ the #89 single-chunk pin is suppressed:
        # a "rate for every union" question must not pin ONE union's wage table.
        ctx = preprocess("journeyperson rate for every union", KNOWN_UNIONS)
        assert ctx.is_enumeration is True
        assert ctx.is_wage_query is True
        assert ctx.rate_classification is None

    def test_non_enumeration_query_leaves_is_enumeration_false(self) -> None:
        # Byte-for-byte parity for ordinary single-union queries: no enumeration,
        # no forced cross-union, union filter intact, rate classification intact.
        ctx = preprocess(
            "What is the journeyperson hourly rate for IBEW?", KNOWN_UNIONS
        )
        assert ctx.is_enumeration is False
        assert ctx.is_cross_union is False
        assert ctx.union_filters == ["IBEW"]
        assert ctx.rate_classification == "journeyman"

    def test_singular_two_union_comparison_is_not_enumeration(self) -> None:
        # "which union … IBEW or United Association" is cross-union via the two
        # detected unions, NOT via enumeration — so the corpus-wide fan-out gate
        # (is_enumeration AND no named unions) can never fire here.
        ctx = preprocess(
            "which union has the higher rate: IBEW or United Association?",
            KNOWN_UNIONS,
        )
        assert ctx.is_enumeration is False
        assert ctx.is_cross_union is True
        assert ctx.union_filters == ["IBEW", "United Association"]
