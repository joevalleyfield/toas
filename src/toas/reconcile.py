# reconcile.py

def _eq(a, b):
    return (
        a.get("role") == b.get("role")
        and a.get("content", "").strip() == b.get("content", "").strip()
    )

def reconcile(transcript_msgs, log_nodes):
    # find longest common prefix
    i = 0
    for t, l in zip(transcript_msgs, log_nodes):
        if _eq(t, l):
            i += 1
        else:
            break

    # everything after prefix is new
    return transcript_msgs[i:]
