package vn.smartprop.comparable;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class ComparableSourceClassifierTest {

    @Test
    void attributionNamesTiniXAndItsLicence() {
        String text = ComparableSourceClassifier.TINIX_ATTRIBUTION;
        assertTrue(text.contains("TiniX"));
        assertTrue(text.contains("CC BY-NC 4.0"));
        assertTrue(text.contains("tham chiếu nghiên cứu"), "the research label must be explicit");
    }

    @Test
    void onlyHttpLinksSurvive() {
        assertEquals("https://example.com/a", ComparableSourceClassifier.safeUrl(" https://example.com/a "));
        assertNull(ComparableSourceClassifier.safeUrl("javascript:alert(1)"));
        assertNull(ComparableSourceClassifier.safeUrl("data:text/html,hi"));
        assertNull(ComparableSourceClassifier.safeUrl("//example.com"));
        assertNull(ComparableSourceClassifier.safeUrl(""));
        assertNull(ComparableSourceClassifier.safeUrl(null));
    }

    @Test
    void oversizedLinksAreDropped() {
        assertNull(ComparableSourceClassifier.safeUrl("https://e.com/" + "a".repeat(2048)));
    }

    @Test
    void sourceLabelsAreHumanReadableAndNeverLeakRawCodes() {
        assertEquals("Chợ Tốt", ComparableSourceClassifier.externalLabel("chotot"));
        assertEquals("CafeLand", ComparableSourceClassifier.externalLabel("CAFELAND"));
        assertEquals("Tin đăng bên ngoài", ComparableSourceClassifier.externalLabel("SOMETHING_NEW"));
        assertEquals("Tin đăng bên ngoài", ComparableSourceClassifier.externalLabel(null));
    }
}
