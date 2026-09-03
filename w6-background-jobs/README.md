### Retries vs Input Validation
A wrong input must be rejected at the door with a 400 Bad Request because deterministic errors will never succeed no matter how many times they are repeated; only transient operational failures (a wrong moment) deserve a retry with backoff.

### Stage 4: Cron Heartbeat Schedule Answers

1. **Daily at 08:00:** The cron expression `0 8 * * *` executes the heartbeat task every single day at 08:00 UTC (at minute 0 of hour 8).
2. **Weekly on Sunday at 22:00:** The cron expression `0 22 * * 0` executes the heartbeat task once a week specifically at 22:00 UTC every Sunday (at minute 0 of hour 22 on weekday 0).




