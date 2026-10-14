export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });
  const text = await response.text();
  if (!response.ok) {
    let detail = text || response.statusText;
    try {
      const body = JSON.parse(text) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* keep the raw body */
    }
    throw new Error(detail);
  }
  return JSON.parse(text) as T;
}
