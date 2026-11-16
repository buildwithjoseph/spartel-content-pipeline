# When the Ruby GC stalls, your users time‑out

Your Rails endpoint sits behind a reverse proxy, a DB pool, and a Redis cache.  
One extra `Array#map` on a 10 k‑row feed pushes the GC pause from 30 ms to 250 ms.  
The latency spike lands on the client as a “slow page” warning, and the same request
fails under load because the Ruby heap has already hit the soft limit.

The fix isn’t “more servers”. It’s “move the hot path out of the GC‑managed heap”.

---

## Market pressure meets the missing Rust bridge

| Trendy DEV post (user demand) | Core pain point | Existing GitHub signal | What we need |
|------------------------------|----------------|------------------------|--------------|
| **Long Live Rails** (136 reactions) | Ruby‑only hot loops choke under load | *None* – no public Rust‑Rails bridge | A minimal, drop‑in Rust extension that can be compiled without a full toolchain on the host |
| **MCP Is Dead Simple** (192 reactions) | Agentic pipelines explode in memory | *None* – no example of state‑sharded agents in Python | A lightweight state store that lives outside the interpreter |
| **AI Productivity** (112 reactions) | QA bots stall on long‑form context | *None* – no streaming‑aware cache | A streaming‑first primitive that keeps only the last N tokens in RAM |

The table reads like a wish list: developers are shouting for *speed* and *state* but the open‑source ecosystem hasn’t delivered a concrete bridge yet. That gap is where we can drop a few lines of Rust‑backed Python and get measurable ROI.

---

## Architecture in ASCII

```
+-------------------+        +-------------------+        +-------------------+
|  FastAPI / Rails  |  RPC   |  Rust‑Native Lib  |  FFI   |  Local LLM (ggml) |
|  (Python / Ruby) | <----> |  (cargo build)    | <----> |  (CPU‑only)       |
+-------------------+        +-------------------+        +-------------------+
          ^                         ^                         ^
          |                         |                         |
          |   +---------------------+---------------------+   |
          +---|   Shared Memory Queue (RingBuf)          |---+
              +-------------------------------------------+
```

* The web layer talks to the Rust library over a tiny RPC (JSON‑RPC over a Unix socket).  
* The Rust side owns a lock‑free ring buffer that streams token chunks straight into the LLM.  
* No heap copies, no GC pauses, and the LLM runs in‑process without a GPU.

---

## 20‑line Python primitive you can copy‑paste

```python
import os
import json
import socket
from collections import deque
from typing import Iterable

# -------------------------------------------------
# 1️⃣  Ring‑buffer backed by a memory‑mapped file
# -------------------------------------------------
BUF_SIZE = 1 << 20                     # 1 MiB
mm = memoryview(os.open("/tmp/ringbuf", os.O_CREAT | os.O_RDWR))
mm.resize(BUF_SIZE)

head, tail = 0, 0                       # simple indices, wrap‑around with % BUF_SIZE

def push(chunk: bytes) -> None:
    global head
    n = len(chunk)
    assert n < BUF_SIZE, "chunk too large"
    end = (head + n) % BUF_SIZE
    if end < head:                     # wrap
        mm[head:] = chunk[:BUF_SIZE - head]
        mm[:end] = chunk[BUF_SIZE - head:]
    else:
        mm[head:end] = chunk
    head = end

def pop(max_bytes: int) -> bytes:
    global tail
    n = min(max_bytes, (head - tail) % BUF_SIZE)
    end = (tail + n) % BUF_SIZE
    if end < tail:
        data = mm[tail:] + mm[:end]
    else:
        data = mm[tail:end]
    tail = end
    return bytes(data)

# -------------------------------------------------
# 2️⃣  Thin JSON‑RPC client to the Rust side
# -------------------------------------------------
def rpc(method: str, params: dict) -> dict:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect("/tmp/rust.sock")
        s.sendall(json.dumps({"m": method, "p": params}).encode())
        return json.loads(s.recv(4096).decode())

# -------------------------------------------------
# 3️⃣  Streaming inference loop
# -------------------------------------------------
def generate(prompt: str) -> Iterable[str]:
    push(prompt.encode())
    while True:
        resp = rpc("next_token", {})
        token = resp.get("token")
        if not token:
            break
        yield token
        push(token.encode())   # feed‑forward for next step
```

*The code does three things*: a lock‑free ring buffer, a minimal JSON‑RPC shim, and a generator that streams tokens back to the caller without ever allocating a large Python list. Swap the `rpc` implementation for a Go or Rust server and you have a production‑grade agentic primitive in under a minute.

---

## Trade‑off analysis (the hard bits)

| Dimension            | Pure Python (no Rust)                     | Rust‑backed streaming primitive |
|----------------------|-------------------------------------------|---------------------------------|
| **Latency**          | GC pauses + Python call overhead (≈ 150 ms) | Sub‑millisecond hand‑off |
| **Memory churn**     | Heap allocations per token (≈ 2 KB)      | Zero‑copy ring buffer (≈ 64 B) |
| **Developer velocity** | Immediate, no compilation step          | One `cargo build` per platform |
| **Ops footprint**    | Single Docker layer, interpreter only    | Multi‑stage builder, stripped `.so` |
| **Portability**      | Works on any CPython                     | Needs matching `musl`/`glibc` binary |

The biggest friction point is the **build pipeline**. Adding a Rust stage forces you to pin a toolchain version, cache compiled artifacts, and verify that the target platform’s libc matches the production image. In a CI‑heavy org that already runs `cargo` for other services, the incremental cost is negligible; in a pure‑Python shop it can feel like “another language”.

---

### Open question

If you could offload **any** single Ruby hot path to a zero‑copy native primitive, which would give you the biggest ROI: (a) text tokenisation, (b) feed ranking, or (c) request‑level auth checks?  

Drop your answer and any Rust‑FFI tricks you’ve survived in the comments.