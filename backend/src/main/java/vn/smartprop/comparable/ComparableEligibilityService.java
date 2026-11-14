package vn.smartprop.comparable;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Locale;
import java.util.Set;
import org.springframework.stereotype.Service;

/** The single place that decides whether a row may appear as a comparable.
 *
 *  Written as pure predicates so each rule is unit-testable without a database.
 *  The SQL also filters most of this, but defence in depth matters here: a
 *  protected holdout or a rental leaking into the ranking would be a real
 *  research-integrity breach, not just a wrong number.
 */
@Service
public class ComparableEligibilityService {

    /** Property types the SmartProp valuation model was trained on. */
    public static final Set<String> SUPPORTED_TYPES = Set.of("HOUSE", "LAND", "APARTMENT", "VILLA");

    /** Plausible asking-price bounds for a total sale price, in VND. */
    public static final BigDecimal MIN_TOTAL_PRICE = new BigDecimal("200000000");
    public static final BigDecimal MAX_TOTAL_PRICE = new BigDecimal("1000000000000");

    public static final BigDecimal MIN_AREA = new BigDecimal("5");
    public static final BigDecimal MAX_AREA = new BigDecimal("50000");

    public boolean supportedType(String normalizedType) {
        return normalizedType != null && SUPPORTED_TYPES.contains(normalizedType.toUpperCase(Locale.ROOT));
    }

    public boolean plausiblePrice(BigDecimal price) {
        return price != null && price.compareTo(MIN_TOTAL_PRICE) >= 0 && price.compareTo(MAX_TOTAL_PRICE) <= 0;
    }

    public boolean plausibleArea(BigDecimal area) {
        return area != null && area.compareTo(MIN_AREA) >= 0 && area.compareTo(MAX_AREA) <= 0;
    }

    /** Rentals and unknown-basis rows are excluded. Step 21.5 measured that
     *  gate_v3.classify() passes 8,036 rentals and drops 22,353 real sales, so
     *  the authoritative transaction_type column is used instead. */
    public boolean saleTransaction(String transactionType) {
        return "SALE".equalsIgnoreCase(transactionType == null ? "" : transactionType.strip());
    }

    public boolean researchEligible(String qualityStatus, boolean representative, boolean protectedHoldout) {
        return "HYBRID_ELIGIBLE_RESEARCH".equals(qualityStatus) && representative && !protectedHoldout;
    }

    /** Never surface the reference property as its own comparable. */
    public boolean notSelf(String referenceId, String candidateId) {
        return referenceId == null || candidateId == null || !referenceId.equals(candidateId);
    }

    /** Both area and price must be within this multiple, or the row is not comparable. */
    public boolean withinEnvelope(BigDecimal refValue, BigDecimal candidateValue, BigDecimal factor) {
        if (refValue == null || candidateValue == null || refValue.signum() <= 0 || candidateValue.signum() <= 0) {
            return false;
        }
        BigDecimal ratio = candidateValue.divide(refValue, 4, RoundingMode.HALF_UP);
        BigDecimal inverse = BigDecimal.ONE.divide(ratio, 4, RoundingMode.HALF_UP);
        return ratio.compareTo(factor) <= 0 && inverse.compareTo(factor) <= 0;
    }
}
