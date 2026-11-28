package vn.smartprop.comparable;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;

import static vn.smartprop.comparable.ComparableDtos.*;

final class ComparableEvidenceSummary {
    private static final int MINIMUM_OBSERVATIONS = 5;

    private ComparableEvidenceSummary() {}

    static Evidence build(Purpose purpose, int retrieved, Map<SourceKind, Cap> caps, DedupeStats dedupe,
                          List<Candidate> cohort, List<Candidate> sample) {
        boolean complete = caps.values().stream().allMatch(Cap::complete);
        // TiniX is research-only and unverified, even for authorized researchers.
        List<Candidate> priced = cohort.stream().filter(c -> c.sourceKind() != SourceKind.TINIX_RESEARCH).toList();
        boolean sufficient = complete && priced.size() >= MINIMUM_OBSERVATIONS;
        Map<SourceKind, Provenance> provenance = new EnumMap<>(SourceKind.class);
        for (SourceKind source : caps.keySet()) {
            provenance.put(source, new Provenance(count(cohort, source), count(sample, source),
                source == SourceKind.TINIX_RESEARCH ? ComparableSourceClassifier.TINIX_ATTRIBUTION : null));
        }
        List<String> limits = new ArrayList<>();
        if (!complete) limits.add("Đã đến giới hạn đọc ứng viên. Tập dữ liệu phù hợp chưa được quét đầy đủ.");
        if (priced.size() < MINIMUM_OBSERVATIONS) limits.add("Cần ít nhất 5 tin công khai hợp lệ sau khi loại trùng để hiển thị trung vị.");
        limits.add("Thống kê dùng giá rao của các tin công khai đủ điều kiện trong tập đã quét, chưa xác nhận giá giao dịch.");
        var stats = new AskingPriceStats(priced.size(),
            sufficient ? median(priced.stream().map(Candidate::askingPriceVnd).toList()) : null,
            sufficient ? median(priced.stream().map(c -> c.askingPriceVnd().divide(c.areaSqm(), 8, RoundingMode.HALF_UP)).toList()) : null);
        return new Evidence(purpose, sufficient ? EvidenceStatus.AVAILABLE : EvidenceStatus.INSUFFICIENT_EVIDENCE,
            retrieved, cohort.size(), sample.size(), dedupe, complete, Map.copyOf(caps), Map.copyOf(provenance), stats, List.copyOf(limits));
    }

    private static int count(List<Candidate> candidates, SourceKind source) {
        return (int) candidates.stream().filter(candidate -> candidate.sourceKind() == source).count();
    }

    private static BigDecimal median(List<BigDecimal> values) {
        var ordered = values.stream().sorted().toList();
        int middle = ordered.size() / 2;
        BigDecimal median = ordered.size() % 2 == 1 ? ordered.get(middle)
            : ordered.get(middle - 1).add(ordered.get(middle)).divide(BigDecimal.valueOf(2));
        return median.setScale(0, RoundingMode.HALF_UP);
    }
}
