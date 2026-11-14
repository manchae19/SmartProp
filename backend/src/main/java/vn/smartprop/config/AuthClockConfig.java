package vn.smartprop.config;
import java.time.Clock;
import org.springframework.context.annotation.*;
@Configuration
public class AuthClockConfig {
    @Bean Clock authClock(){return Clock.systemUTC();}
}
