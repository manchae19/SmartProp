# WP-02 Comparable evidence API

The endpoint is POST /api/v1/properties/comparables. An active BROKER or ADMIN session can request SAFE evidence. Research requires explicit opt-in, an active ADMIN session and the server-side research flag. The response remains private and no-store. SAFE requests use only SmartProp and eligible external sources.

## Request

| Field | Meaning |
| --- | --- |
| purpose | SIMILAR_LISTING, BUYER_BUDGET_SEARCH or VALUATION_SUPPORT. Omitted purpose retains SIMILAR_LISTING for compatibility. |
| propertyId | A published, unexpired VND total-sale listing. Its physical criteria override free-form fields. Omit for a standalone estimate or unpublished draft. |
| propertyType, district, ward, areaSqm | Strict comparable criteria. An explicit ward excludes sources that lack a verified ward. |
| priceVnd | Asking-price reference for SIMILAR_LISTING. VALUATION_SUPPORT ignores it, including the price on the propertyId path. |
| buyerBudgetVnd | Absolute inclusive upper bound for BUYER_BUDGET_SEARCH. Legacy priceVnd is accepted as that purpose's budget when buyerBudgetVnd is absent. |
| bedrooms, floors, physicalFeatures | Optional observed physical features. physicalFeatures accepts frontageM, roadWidthM and projectId. Frontage and road width are unavailable in the public source projections. Apartment project comparison uses explicit project identity where available. |
| subjectIdentity | Optional external ID, vendor-scoped listing ID, TiniX ID or canonical listing URL for self-match exclusion. |
| limit | Number of returned rows, from 1 to 5. |

## Response

The legacy fields reference, candidateCount, searchStage, comparables, warnings and eligibleCountsBySource remain. candidateCount is the returned sample size. The optional featureCoverage field on each candidate reports the fraction of applicable feature weight with values available on both sides. similarityScore is a heuristic in [0,1].

The additive evidence object reports:

- purpose and status. INSUFFICIENT_EVIDENCE keeps any usable example rows and withholds both medians.
- retrievedCandidateCount counts distinct source-qualified IDs considered from batches, before Java eligibility and identity resolution. Duplicate reads and the final overflow sentinel are excluded.
- uniqueEligibleCandidateCount and returnedSampleCount distinguish the deduplicated scanned cohort from top-K.
- dedupe includes eligibleBeforeDedupe, exactSelfExcluded and duplicateRowsRemoved among distinct retrieved IDs. Sources can also exclude exact IDs in SQL before retrieval.
- scanComplete and caps report completeness and initial and expanded limits per source. One bounded reread uses the same filter and sort, with a sentinel to detect an incomplete scan. SIMILAR_LISTING retains its existing wider asking-price search for a short result. It does not broaden district or type.
- provenance counts each source in the deduplicated cohort and the returned sample. Research attribution appears only on the authorized research path.
- scannedCohortAskingPrice includes the number of eligible deduplicated public asking prices, medianPriceVnd and medianPricePerSqmVnd. The latter is the median of per-listing ratios. The policy requires at least five observations and a complete scan. Rates and prices round to the nearest VND. Authorized research rows remain in their own provenance and are excluded from public asking-price statistics.
- limitations explain scan bounds and how to interpret the asking-price evidence.

Unified Advisor exposes comparableEvidence for SIMILAR_LISTING and valuationComparableEvidence for independent VALUATION_SUPPORT when requested and a valuation is available. Each can carry the additive cohort object above. The valuation-support cohort is always SAFE. The response and calculation of V1.3, including its explanation contract, stay independent of both comparable results.
