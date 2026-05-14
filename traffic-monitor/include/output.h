#ifndef TRAFFIC_MONITOR_OUTPUT_H
#define TRAFFIC_MONITOR_OUTPUT_H

/* Render the current stats snapshot to `path` as JSON, using a tmp file +
 * rename for atomic publication. Returns 0 on success, -1 on error
 * (errno set; the caller is expected to log and continue). */
int output_write_json(const char *path);

#endif /* TRAFFIC_MONITOR_OUTPUT_H */
