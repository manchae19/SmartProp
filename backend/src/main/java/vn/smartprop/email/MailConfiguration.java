package vn.smartprop.email;
import org.springframework.context.annotation.*;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.mail.javamail.*;
@Configuration
public class MailConfiguration {
    @Bean @ConditionalOnMissingBean(MailTransport.class)
    MailTransport smtp(@Value("${app.email.smtp-host:}") String host,@Value("${app.email.smtp-port:587}") int port,@Value("${app.email.smtp-user:}") String user,@Value("${app.email.smtp-password:}") String password,@Value("${app.email.sender:}") String sender){
        return new MailTransport(){
            public boolean configured(){return !host.isBlank()&&!sender.isBlank();}
            public void send(String recipient,String purpose,String link,String messageId)throws Exception{
                if(!configured())throw new IllegalStateException("Mail unavailable");
                var smtp=new JavaMailSenderImpl();smtp.setHost(host);smtp.setPort(port);smtp.setUsername(user);smtp.setPassword(password);
                var props=smtp.getJavaMailProperties();props.setProperty("mail.smtp.starttls.enable","true");props.setProperty("mail.smtp.starttls.required","true");props.setProperty("mail.smtp.auth",Boolean.toString(!user.isBlank()));props.setProperty("mail.smtp.connectiontimeout","10000");props.setProperty("mail.smtp.timeout","10000");props.setProperty("mail.smtp.writetimeout","10000");props.setProperty("mail.debug","false");
                var message=smtp.createMimeMessage();var helper=new MimeMessageHelper(message,"UTF-8");helper.setFrom(sender);helper.setTo(recipient);helper.setSubject(purpose.equals("PASSWORD_RESET")?"SmartProp password recovery":"SmartProp email verification");helper.setText("Open this link to continue:\n"+link,false);message.setHeader("Message-ID","<"+messageId+"@smartprop.local>");smtp.send(message);
            }
        };
    }
}
