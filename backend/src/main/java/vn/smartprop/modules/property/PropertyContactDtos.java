package vn.smartprop.modules.property;

public final class PropertyContactDtos {
    private PropertyContactDtos() {}
    public record Contact(boolean available, String contactName, String contactPhone, String contactEmail) {}
}
