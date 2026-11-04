package vn.smartprop.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.web.embedded.tomcat.TomcatServletWebServerFactory;
import org.springframework.boot.web.server.WebServerFactoryCustomizer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/** Optional transport fallback for Windows hosts whose selector loopback cannot start. */
@Configuration
public class LocalWebServerConfig {
    public enum Transport { NIO, NIO2 }
    @Bean WebServerFactoryCustomizer<TomcatServletWebServerFactory> tomcatTransport(
            @Value("${app.server.transport:NIO}") Transport transport) {
        return factory -> factory.setProtocol(transport==Transport.NIO2
            ? "org.apache.coyote.http11.Http11Nio2Protocol"
            : "org.apache.coyote.http11.Http11NioProtocol");
    }
}
