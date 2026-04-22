// 🔹 Normalize AI text into base category
export function normalizeType(text: string) {
  const t = text.toLowerCase();

  if (t.includes("pump")) return "pump";
  if (t.includes("valve")) return "valve";
  if (t.includes("heat")) return "heat exchanger";
  if (t.includes("tank") || t.includes("vessel")) return "tank";

  return t;
}

// 🔹 Match AI component to real component
export function matchComponent(searchText: string, allComps: any[]) {
  const normalized = normalizeType(searchText);

  let bestMatch = null;
  let bestScore = -1;

  allComps.forEach((c: any) => {
    const name = c.name?.toLowerCase() || "";
    const object = c.object?.toLowerCase() || "";

    let score = 0;

    // ✅ Exact match (highest priority)
    if (name === searchText || object === searchText) {
      score = 100;
    }
    // ✅ Partial match
    else if (name.includes(searchText) || object.includes(searchText)) {
      score = 70;
    }
    // ✅ Normalized fallback
    else if (name.includes(normalized) || object.includes(normalized)) {
      score = 40;
    }

    if (score > bestScore) {
      bestScore = score;
      bestMatch = c;
    }
  });

  return bestMatch;
}
