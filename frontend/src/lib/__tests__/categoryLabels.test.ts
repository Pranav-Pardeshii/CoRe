import { describe, expect, it } from "vitest";
import { decodeCategory, decodeSeatLevel } from "../categoryLabels";

describe("decodeCategory", () => {
  it("decodes All and ALL consistently", () => {
    expect(decodeCategory("All").displayText).toBe("All Categories (All)");
    expect(decodeCategory("ALL").displayText).toBe("All Categories (All)");
  });

  it("decodes standard structured CET codes", () => {
    expect(decodeCategory("GOPENS").displayText).toBe("General Open — State Level (GOPENS)");
    expect(decodeCategory("LOBCH").displayText).toBe("Ladies-only OBC — Home University (LOBCH)");
    expect(decodeCategory("GNT1O").displayText).toBe(
      "General NT1 — Other than Home University (GNT1O)",
    );
    expect(decodeCategory("DEFOPENS").displayText).toBe("Defence Open — State Level (DEFOPENS)");
    expect(decodeCategory("PWDROBCS").displayText).toBe(
      "PWD (Common Reserved) OBC — State Level (PWDROBCS)",
    );
  });

  it("decodes standalone quotas", () => {
    expect(decodeCategory("TFWS").displayText).toBe("Tuition Fee Waiver Scheme (TFWS)");
    expect(decodeCategory("EWS").displayText).toBe("Economically Weaker Section (EWS)");
    expect(decodeCategory("ORPHAN").displayText).toBe("Orphan Quota (ORPHAN)");
    expect(decodeCategory("MI").displayText).toBe("Minority Quota (MI)");
    expect(decodeCategory("AI").displayText).toBe("All India Quota (AI)");
  });

  it("handles dataset edge variants and falls back gracefully on unknown codes", () => {
    expect(decodeCategory("DEFRSEBC").displayText).toBe("Defence (Common Reserved) SEBC (DEFRSEBC)");
    expect(decodeCategory("DEFRNT1SS").displayText).toBe(
      "Defence (Common Reserved) NT1 — State Level (DEFRNT1SS)",
    );
    expect(decodeCategory("CUSTOM99").displayText).toBe("CUSTOM99");
  });

  it("decodes seat allocation levels", () => {
    expect(decodeSeatLevel("SL")).toBe("State Level");
    expect(decodeSeatLevel("HU_HU")).toBe("Home University (Home Seat)");
    expect(decodeSeatLevel("UNKNOWN")).toBe("UNKNOWN");
  });
});
