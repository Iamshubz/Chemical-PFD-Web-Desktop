import { describe, it, expect } from "vitest";
import { matchComponent, normalizeType } from "@/utils/aiMatcher";

const mockComponents = [
  { name: "control valve", object: "valve" },
  { name: "gate valve", object: "valve" },
  { name: "centrifugal pump", object: "pump" },
  { name: "heat exchanger", object: "heat exchanger" },
  { name: "tank", object: "tank" },
];

describe("normalizeType", () => {
  it("normalizes pump", () => {
    expect(normalizeType("centrifugal pump")).toBe("pump");
  });

  it("normalizes valve", () => {
    expect(normalizeType("control valve")).toBe("valve");
  });

  it("normalizes tank/vessel", () => {
    expect(normalizeType("vertical vessel")).toBe("tank");
  });
});

describe("matchComponent", () => {
  it("returns exact match when available", () => {
    const result = matchComponent("control valve", mockComponents);
    expect(result).not.toBeNull();
    expect(result!.name).toBe("control valve");
  });

  it("returns best match for generic input", () => {
    const result = matchComponent("valve", mockComponents);
    expect(result).not.toBeNull();
    expect(result!.object).toBe("valve");
  });

  it("returns normalized match", () => {
    const result = matchComponent("heat", mockComponents);
    expect(result).not.toBeNull();
    expect(result!.name).toBe("heat exchanger");
  });

  it("returns fallback match when unknown", () => {
    const result = matchComponent("unknown component", mockComponents);
    expect(result).not.toBeNull();
  });
});