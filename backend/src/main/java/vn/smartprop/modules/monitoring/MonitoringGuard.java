package vn.smartprop.modules.monitoring;

import java.util.function.Consumer;
import java.util.function.Supplier;

import static vn.smartprop.modules.monitoring.MonitoringSchema.Drop;

/** Failure isolation for future call sites. The business operation stays outside telemetry catches. */
public final class MonitoringGuard {
    private MonitoringGuard() {}

    public static boolean observe(SpringTelemetry recorder, Runnable observation) {
        if (!recorder.enabled()) {
            return false;
        }
        try {
            observation.run();
            return true;
        } catch (RuntimeException failure) {
            recorder.drop(Drop.MONITOR_FAULT);
            return false;
        }
    }

    public static <T> T around(SpringTelemetry recorder, Runnable before, Supplier<T> operation,
                               Consumer<Boolean> after) {
        if (!recorder.enabled()) {
            return operation.get();
        }
        observe(recorder, before);
        boolean returned = false;
        try {
            T result = operation.get();
            returned = true;
            return result;
        } finally {
            boolean completed = returned;
            observe(recorder, () -> after.accept(completed));
        }
    }
}
