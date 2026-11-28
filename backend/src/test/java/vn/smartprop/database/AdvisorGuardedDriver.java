package vn.smartprop.database;
import java.sql.*;
import java.util.*;
import java.util.logging.Logger;
/** No physical connection is delegated until the exact independent fixture boundary passes. */
public final class AdvisorGuardedDriver implements Driver {
    private final Driver driver=new com.mysql.cj.jdbc.Driver();
    public AdvisorGuardedDriver() throws SQLException {}
    public Connection connect(String url,Properties properties) throws SQLException {
        var fixture=AdvisorFixtureBoundary.AUTHORIZED.get(url);
        if(fixture==null)throw new SQLException("Unallocated JDBC destination blocked before connect");
        try{fixture.verify(url);}catch(RuntimeException e){throw new SQLException("Pre-connection fixture rejection",e);}
        AdvisorFixtureBoundary.PHYSICAL_CONNECTIONS.add(url);
        return driver.connect(url,properties);
    }
    public boolean acceptsURL(String url)throws SQLException{return driver.acceptsURL(url);}
    public DriverPropertyInfo[] getPropertyInfo(String url,Properties p)throws SQLException{return driver.getPropertyInfo(url,p);}
    public int getMajorVersion(){return driver.getMajorVersion();}public int getMinorVersion(){return driver.getMinorVersion();}
    public boolean jdbcCompliant(){return driver.jdbcCompliant();}public Logger getParentLogger(){return Logger.getGlobal();}
}
