import { expect, test } from "@playwright/test";

test("home redirects to the review page inside the app shell", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/review$/);
  await expect(page.getByRole("heading", { name: "Sibyl" })).toBeVisible();
});
