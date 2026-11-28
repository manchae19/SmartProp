package vn.smartprop.modules.monitoring;

import java.net.ConnectException;
import java.net.SocketTimeoutException;
import java.net.UnknownHostException;
import java.net.http.HttpTimeoutException;
import java.util.concurrent.CancellationException;
import java.util.concurrent.CompletionException;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeoutException;

import static vn.smartprop.modules.monitoring.MonitoringSchema.Outcome;

/** Classification at the outbound client, before its business exception translation. */
public final class DispatchOutcome {
    private DispatchOutcome() {}

    public static Outcome response(int status) {
        return status >= 200 && status <= 599 ? Outcome.AI_RESPONSE : Outcome.FAILED;
    }

    public static Outcome failure(Throwable cause) {
        for (int depth = 0; depth < 4 && (cause instanceof CompletionException
                || cause instanceof ExecutionException); depth++) {
            cause = cause.getCause();
        }
        if (cause instanceof TimeoutException || cause instanceof HttpTimeoutException
                || cause instanceof SocketTimeoutException) {
            return Outcome.TIMEOUT;
        }
        if (cause instanceof CancellationException || cause instanceof InterruptedException) {
            return Outcome.CANCELLED;
        }
        if (cause instanceof ConnectException || cause instanceof UnknownHostException) {
            return Outcome.DEPENDENCY_UNAVAILABLE;
        }
        return Outcome.FAILED;
    }
}
