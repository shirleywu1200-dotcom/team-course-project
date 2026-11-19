import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { MemoryRouter } from "react-router-dom";

import { todayFixtures } from "../../test/fixtures";
import { makeQueryClient } from "../../api/queryClient";
import { API, server } from "../../test/server";
import { FeedbackForm } from "./FeedbackForm";

test("AC-45：填寫中量表版本改變仍送出開啟時擷取的 rubric_id", async () => {
  const bodies: unknown[] = [];
  server.use(http.put(`${API}/tasks/103/feedback`, async ({ request }) => {
    bodies.push(await request.json());
    return HttpResponse.json(todayFixtures.savedFeedback, { status: 201 });
  }));
  const user = userEvent.setup();
  const client = makeQueryClient();
  const { rerender } = render(<QueryClientProvider client={client}><MemoryRouter>
    <FeedbackForm taskId={103} rubricId={1} /></MemoryRouter></QueryClientProvider>);
  await user.selectOptions(screen.getByLabelText("實際達成星數"), "4");
  rerender(<QueryClientProvider client={client}><MemoryRouter>
    <FeedbackForm taskId={103} rubricId={2} /></MemoryRouter></QueryClientProvider>);
  await user.selectOptions(screen.getByLabelText("自評精力"), "mid");
  await user.click(screen.getByRole("button", { name: "儲存完成回報" }));
  await waitFor(() => expect(bodies).toEqual([{ actual_stars: 4, energy: "mid", rubric_id: 1 }]));
});
