package vn.smartprop.modules.prepurchase;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Listings write the street two ways: "Đường Trần Cao Vân, …" and "Kiệt Trần Cao Vân, …".
 * Both name the same street, so both must be read; the alley number is dropped because
 * the catalogue records a street, not a house.
 *
 * <p>Reading the alley form must not weaken the ward check: a listing on Nguyễn Lương
 * Bằng in Hòa Khánh still only matches the Hòa Khánh records, never the Hải Vân one.
 */
class PrePurchaseStreetOfTest {
    @Test
    void readsStreetAfterDuong() {
        assertEquals("Trần Cao Vân", PrePurchaseService.streetOf("Đường Trần Cao Vân, Tân Chính"));
        assertEquals("Nguyễn Tất Thành", PrePurchaseService.streetOf("Đường Nguyễn Tất Thành"));
    }

    @Test
    void readsStreetAfterKietWithoutNumber() {
        assertEquals("Trần Cao Vân", PrePurchaseService.streetOf("Kiệt Trần Cao Vân, Thanh Khê Đông"));
        assertEquals("Nguyễn Tri Phương", PrePurchaseService.streetOf("Kiệt Nguyễn Tri Phương, Chính Gián"));
    }

    @Test
    void readsStreetAfterKietWithNumber() {
        assertEquals("Điện Biên Phủ", PrePurchaseService.streetOf("Kiệt 350 Điện Biên Phủ, Chính Gián"));
        assertEquals("Hà Huy Tập", PrePurchaseService.streetOf("Kiệt 96 Hà Huy Tập, Thanh Khê"));
    }

    @Test
    void prefersDuongOverBareAlleyNumber() {
        // "Kiệt 350" chỉ là số kiệt; tên đường nằm ở phần "Đường …" phía sau.
        assertEquals("Điện Biên Phủ",
            PrePurchaseService.streetOf("Kiệt 350, Đường Điện Biên Phủ, Chính Gián"));
    }

    @Test
    void returnsNullWhenOnlyAnAlleyNumberIsGiven() {
        // Không có tên đường nào trong địa chỉ: số kiệt không được dùng làm tên đường.
        assertNull(PrePurchaseService.streetOf("Kiệt 350, Chính Gián"));
        assertNull(PrePurchaseService.streetOf("Kiệt 350"));
    }

    @Test
    void ignoresAddressWithoutStreet() {
        assertNull(PrePurchaseService.streetOf("Đường Phan Xích Long".replace("Đường ", "")));
        assertNull(PrePurchaseService.streetOf("Hòa An"));
        assertNull(PrePurchaseService.streetOf(null));
        assertNull(PrePurchaseService.streetOf("  "));
    }

    @Test
    void keepsWardCheckIntact() {
        // Cùng tên đường, khác phường: bản ghi Hải Vân không được khớp với tin Hòa Khánh.
        var haiVan = new PrePurchaseRepository.Flood("PL8-III-07", "PLANNED_RISK",
            "Kiệt 455, đường Nguyễn Lương Bằng", "Nguyễn Lương Bằng", null, "Liên Chiểu",
            "AREA", null, null, null, "https://example.invalid", "Phụ lục VIII", null,
            "Phường Hải Vân", "OSM_ADDRESS");
        var lienChieu = new PrePurchaseRepository.Flood("PL8-III-09", "PLANNED_RISK",
            "Kiệt 383, đường Nguyễn Lương Bằng", "Nguyễn Lương Bằng", null, "Liên Chiểu",
            "AREA", null, null, null, "https://example.invalid", "Phụ lục VIII", null,
            "Phường Liên Chiểu", "OSM_ADDRESS");

        String street = PrePurchaseService.streetOf("Kiệt Nguyễn Lương Bằng, Hòa Khánh Bắc");
        assertEquals("Nguyễn Lương Bằng", street);

        assertNull(PrePurchaseService.floodMatch(haiVan, street, "Phường Liên Chiểu"),
            "bản ghi Hải Vân không được khớp với tin Phường Liên Chiểu");
        assertEquals(PrePurchaseService.Match.STREET,
            PrePurchaseService.floodMatch(lienChieu, street, "Phường Liên Chiểu"));
    }
}
