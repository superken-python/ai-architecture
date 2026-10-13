// Client AG-UI tối giản: POST RunAgentInput tới AgentOS, đọc stream SSE, trả lần lượt từng sự kiện.
// Không cần thư viện: giao thức chỉ là JSON qua `data:` của Server-Sent Events.

export async function* runAgui(url, input, signal) {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(input),
    signal,
  });
  if (!resp.ok || !resp.body) {
    const detail = await resp.text().catch(() => "");
    throw new Error(`AG-UI trả lỗi HTTP ${resp.status}${detail ? `: ${detail.slice(0, 200)}` : ""}`);
  }
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let cut;
    while ((cut = buffer.indexOf("\n\n")) >= 0) {
      const chunk = buffer.slice(0, cut);
      buffer = buffer.slice(cut + 2);
      const data = chunk
        .split("\n")
        .filter((l) => l.startsWith("data:"))
        .map((l) => l.slice(5).trimStart())
        .join("\n");
      if (data) yield JSON.parse(data);
    }
  }
}
