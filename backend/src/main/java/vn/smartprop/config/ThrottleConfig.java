package vn.smartprop.config;
import vn.smartprop.security.LoginThrottle;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.*;
@Configuration
public class ThrottleConfig {
    @Bean LoginThrottle loginThrottle(ObjectMapper mapper) { return new LoginThrottle(mapper); }
    @Bean FilterRegistrationBean<LoginThrottle> disableServletRegistration(LoginThrottle throttle) {
        var registration=new FilterRegistrationBean<>(throttle); registration.setEnabled(false); return registration;
    }
}
