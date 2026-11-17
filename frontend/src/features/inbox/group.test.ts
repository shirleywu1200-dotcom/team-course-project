import type { CandidateKind } from "../../api/types";
import { makeCandidate } from "../../test/server";
import { groupCandidates } from "./group";

test("五種候選各落在正確的區", () => {
  const kinds: CandidateKind[] = ["delay", "done", "stuck", "unclear", "unmatched"];
  const groups = groupCandidates(kinds.map((kind, i) => makeCandidate({ id: i, kind })));
  expect(groups.sure.map((c) => c.kind)).toEqual(["delay", "done", "stuck"]);
  expect(groups.unclear.map((c) => c.kind)).toEqual(["unclear"]);
  expect(groups.unmatched.map((c) => c.kind)).toEqual(["unmatched"]);
});
