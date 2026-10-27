package vn.smartprop.property;

public final class PropertyContactDtos {
    private PropertyContactDtos() {}
    public record Contact(boolean available, String contactName, String contactPhone, String contactEmail) {}
}
