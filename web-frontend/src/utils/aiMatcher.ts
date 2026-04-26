// 🔹 Define proper type (THIS is the key fix)
export type Component = {
  name: string;
  object: string;
};

// 🔹 Normalize AI text into base category
export function normalizeType(text: string): string {
  const t = text.toLowerCase();

  if (t.includes("pump")) return "pump";
  if (t.includes("valve")) return "valve";
  if (t.includes("heat")) return "heat exchanger";
  if (t.includes("tank") || t.includes("vessel")) return "tank";

  return t;
}

// 🔹 Match AI component to real component
export function matchComponent(
  searchText: string,
  allComps: Component[]
): Component | null {
  const normalized = normalizeType(searchText.toLowerCase());

  let bestMatch: Component | null = null;
  let bestScore = -1;

  allComps.forEach((c) => {
    const name = c.name.toLowerCase();
    const object = c.object.toLowerCase();

    let score = 0;

    // ✅ Exact match
    if (name === searchText.toLowerCase() || object === searchText.toLowerCase()) {
      score = 100;
    }
    // ✅ Partial match
    else if (name.includes(searchText.toLowerCase()) || object.includes(searchText.toLowerCase())) {
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