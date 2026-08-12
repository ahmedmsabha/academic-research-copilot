import { describe, expect, it } from "vitest";

import type { Citation } from "@/types/api";

function formatCitationLabel(citation: Pick<Citation, "filename" | "page_start" | "page_end">): string {
  if (citation.page_start == null) {
    return citation.filename;
  }
  if (citation.page_end == null || citation.page_end === citation.page_start) {
    return `${citation.filename}, p. ${citation.page_start}`;
  }
  return `${citation.filename}, pp. ${citation.page_start}–${citation.page_end}`;
}

describe("citation labels", () => {
  it("formats a single page", () => {
    expect(
      formatCitationLabel({
        filename: "thesis.pdf",
        page_start: 4,
        page_end: 4,
      }),
    ).toBe("thesis.pdf, p. 4");
  });

  it("formats a page range", () => {
    expect(
      formatCitationLabel({
        filename: "thesis.pdf",
        page_start: 4,
        page_end: 6,
      }),
    ).toBe("thesis.pdf, pp. 4–6");
  });
});
