package vn.smartprop.email;
public interface MailTransport {
    boolean configured();
    void send(String recipient,String purpose,String link,String messageId) throws Exception;
}
