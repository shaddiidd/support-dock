import { render, screen } from "@testing-library/react";

import App from "./App";

test("renders the sign in screen by default", () => {
  render(<App />);
  expect(screen.getByRole("heading", { name: /sign in/i })).toBeInTheDocument();
});
