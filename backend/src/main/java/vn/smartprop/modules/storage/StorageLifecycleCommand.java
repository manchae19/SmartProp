package vn.smartprop.modules.storage;
import java.nio.file.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.boot.*;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.stereotype.Component;
import org.springframework.core.env.Environment;
@Component @ConditionalOnProperty(name="app.storage-lifecycle.command")
public class StorageLifecycleCommand implements ApplicationRunner {
    private final StorageLifecycle storage;private final Environment env;private final ObjectMapper json;private final ConfigurableApplicationContext context;
    public StorageLifecycleCommand(StorageLifecycle storage,Environment env,ObjectMapper json,ConfigurableApplicationContext context){this.storage=storage;this.env=env;this.json=json;this.context=context;}
    public void run(ApplicationArguments args)throws Exception{try{String command=env.getRequiredProperty("app.storage-lifecycle.command");if(command.equals("scan")){Path out=Path.of(env.getRequiredProperty("app.storage-lifecycle.report"));var entries=storage.scan(7);Files.write(out,json.writeValueAsBytes(entries),StandardOpenOption.CREATE_NEW);System.out.println("Storage dry-run complete; entries="+entries.size()+"; no files moved");}else if(command.equals("quarantine")){storage.quarantine(env.getRequiredProperty("app.storage-lifecycle.key"),env.getRequiredProperty("app.storage-lifecycle.sha256"),Path.of(env.getRequiredProperty("app.storage-lifecycle.backup")),env.getProperty("app.storage-lifecycle.writers-paused",Boolean.class,false));System.out.println("Quarantine complete; original bytes retained; no permanent deletion");}else if(command.equals("restore")){storage.restore(env.getRequiredProperty("app.storage-lifecycle.receipt"));System.out.println("Quarantine restore complete");}else throw new IllegalArgumentException("Supported commands: scan, quarantine, restore; no purge");}finally{context.close();}}
}
