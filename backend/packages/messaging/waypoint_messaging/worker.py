"""At-least-once worker: commit handler effects before acknowledgement."""

import logging
import signal
import threading

from . import decode_message


def consume(queue, handle, stop=None):
    stop = stop or threading.Event()
    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGTERM, lambda *_: stop.set())
        signal.signal(signal.SIGINT, lambda *_: stop.set())
    while not stop.is_set():
        try:
            messages = queue.receive()
        except Exception:
            logging.exception("queue receive failed")
            stop.wait(2)
            continue
        for message in messages:
            finished = threading.Event()

            def heartbeat():
                while not finished.wait(40):
                    try:
                        queue.extend(message)
                    except Exception:
                        logging.exception("visibility renewal failed")

            thread = threading.Thread(target=heartbeat, daemon=True)
            thread.start()
            try:
                from waypoint_observability import correlation_id, traceparent

                envelope = decode_message(message.body)
                correlation_token = correlation_id.set(envelope.correlation_id)
                trace_token = traceparent.set(envelope.traceparent)
                try:
                    handle(envelope)
                finally:
                    correlation_id.reset(correlation_token)
                    traceparent.reset(trace_token)
                queue.acknowledge(message)
            except Exception:
                # SQS redrive policy moves repeatedly failing/poison messages to the DLQ.
                # Do not log the body, which can contain private operational data.
                logging.exception("message processing failed")
                queue.retry(message)
            finally:
                finished.set()
                thread.join(timeout=1)


def publish_loop(publish):
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    failures = 0
    while not stop.is_set():
        try:
            published = publish()
        except Exception:
            logging.exception("outbox iteration failed")
            published = -1
        if published < 0:
            failures += 1
            stop.wait(min(30, 2 ** min(failures, 5)))
        else:
            failures = 0
            if published == 0:
                stop.wait(1)
