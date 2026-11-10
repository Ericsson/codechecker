import { createSSRApp, h } from "vue";
import { renderToString } from "vue/server-renderer";
import { ReviewStatus } from "@cc/report-server-types";
import SelectReviewStatus from "../SelectReviewStatus.vue";

jest.mock("@/components/Icons", () => ({
  ReviewStatusIcon: { render: () => null }
}));

// Renders the ids of the items offered by the select as a comma-separated
// string, so no DOM is needed.
const VSelectStub = {
  props: [ "items" ],
  render() {
    return h("div", this.items.map(i => i.id).join(","));
  }
};

async function itemIds(props = {}) {
  const app = createSSRApp({
    render: () => h(SelectReviewStatus, props)
  });
  app.component("VSelect", VSelectStub);
  const html = await renderToString(app);
  return html.replace(/<[^>]+>/g, "").split(",").map(Number);
}

describe("SelectReviewStatus", () => {
  it("offers every review status by default", async () => {
    expect(await itemIds()).toEqual(Object.values(ReviewStatus));
  });

  it("omits Unreviewed when excludeUnreviewed is set", async () => {
    const ids = await itemIds({ excludeUnreviewed: true });
    expect(ids).not.toContain(ReviewStatus.UNREVIEWED);
    expect(ids).toEqual(
      Object.values(ReviewStatus).filter(v => v !== ReviewStatus.UNREVIEWED)
    );
  });
});
