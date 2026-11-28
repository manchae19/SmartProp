package vn.smartprop.modules.monitoring;

/** Server-side call sites choose a boundary. No request header is an input to this contract. */
public final class TrustedOrigin {
    public enum Surface { STANDALONE, POSTING, ADVISOR, UNATTRIBUTED }

    public enum Population {
        PRIMARY(1), SYNTHETIC(2), PREVIEW(3), INTERNAL_DIAGNOSTIC(4), HISTORICAL_COMPATIBILITY(5);

        private final int wireCode;

        Population(int wireCode) {
            this.wireCode = wireCode;
        }

        int wireCode() {
            return wireCode;
        }
    }

    public enum Boundary {
        VERIFIED_STANDALONE_PROXY(Surface.STANDALONE, Population.PRIMARY),
        POSTING_CONTROLLER(Surface.POSTING, Population.PRIMARY),
        ADVISOR_CONTROLLER(Surface.ADVISOR, Population.PRIMARY),
        UNVERIFIED(Surface.UNATTRIBUTED, Population.PRIMARY),
        INTERNAL_PREVIEW(Surface.UNATTRIBUTED, Population.PREVIEW),
        INTERNAL_DIAGNOSTIC(Surface.UNATTRIBUTED, Population.INTERNAL_DIAGNOSTIC),
        HISTORICAL_COMPATIBILITY(Surface.UNATTRIBUTED, Population.HISTORICAL_COMPATIBILITY);

        private final Scope scope;

        Boundary(Surface surface, Population population) {
            scope = new Scope(surface, population);
        }
    }

    public record Scope(Surface surface, Population population) {}

    private TrustedOrigin() {}

    public static Scope classify(Boundary boundary) {
        return (boundary == null ? Boundary.UNVERIFIED : boundary).scope;
    }

    static boolean accepts(Population recorder, Scope scope) {
        return recorder == scope.population()
                || recorder == Population.SYNTHETIC && scope.population() == Population.PRIMARY;
    }
}
