package vn.smartprop.modules.amenity;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.sql.SQLException;
import java.util.*;
import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.*;
import org.springframework.jdbc.core.*;
import org.springframework.jdbc.BadSqlGrammarException;

class AmenityMapFallbackTest {
    final JdbcTemplate jdbc=mock(JdbcTemplate.class);
    final GeoapifyDistrictPlaces live=mock(GeoapifyDistrictPlaces.class);
    final AmenityMapService service=new AmenityMapService(jdbc,new AmenityCatalogService(new ObjectMapper()),mock(AmenityMapBoundaryCatalog.class),live);
    @Test void mallIsSupportedAndEmptyVerifiedResultsUseDistrictProvider() {
        when(jdbc.query(anyString(),any(RowMapper.class),any(Object[].class))).thenReturn(List.of());
        service.find("Hải Châu","MALL");verify(live).find("Hải Châu","MALL");
    }
    @Test void missingViewUsesProviderWithoutImportingAnything() {
        when(jdbc.query(anyString(),any(RowMapper.class),any(Object[].class))).thenThrow(new BadSqlGrammarException("test","test",new SQLException("missing view","42S02",1146)));
        service.find("Hải Châu","HOSPITAL");verify(live).find("Hải Châu","HOSPITAL");
    }
    @Test void unrelatedSqlErrorsAreNotHiddenByFallback() {
        var failure=new BadSqlGrammarException("test","test",new SQLException("unknown column","42S22",1054));
        when(jdbc.query(anyString(),any(RowMapper.class),any(Object[].class))).thenThrow(failure);
        assertSame(failure,assertThrows(BadSqlGrammarException.class,()->service.find("Hải Châu","HOSPITAL")));verifyNoInteractions(live);
    }
}
