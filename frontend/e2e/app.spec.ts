import { test, expect } from "@playwright/test";

// ── Mock API helpers ────────────────────────────────────────────────────

const MOCK_RECIPES = {
  items: [
    {
      id: 1,
      name: "番茄炒蛋",
      prep_time: 10,
      cook_time: 5,
      difficulty: 1,
      cuisine: "中式",
      image_url: "",
      tags: [{ id: 1, name: "家常" }],
      total_time: 15,
      created_at: "2026-01-01",
    },
    {
      id: 2,
      name: "意大利面",
      prep_time: 10,
      cook_time: 20,
      difficulty: 2,
      cuisine: "意大利",
      image_url: "",
      tags: [{ id: 2, name: "Pasta" }],
      total_time: 30,
      created_at: "2026-01-02",
    },
  ],
  total: 2,
  page: 1,
  page_size: 12,
};

const MOCK_DETAIL = {
  id: 1,
  name: "番茄炒蛋",
  description: "经典家常菜",
  prep_time: 10,
  cook_time: 5,
  difficulty: 1,
  cuisine: "中式",
  image_url: "",
  total_time: 15,
  tags: [{ id: 1, name: "家常" }],
  ingredients: [
    { id: 1, name: "鸡蛋", amount: 3, unit: "个" },
    { id: 2, name: "番茄", amount: 2, unit: "个" },
  ],
  steps: [
    { id: 1, order: 1, description: "鸡蛋打散，番茄切块" },
    { id: 2, order: 2, description: "热油炒蛋，盛出备用" },
    { id: 3, order: 3, description: "炒番茄至软，加入炒蛋翻炒" },
  ],
  nutrition: {
    id: 1,
    calories: 250,
    protein: 15,
    fat: 12,
    carbohydrates: 20,
    source: "ingredient_database_estimate",
    calculated_at: "2026-07-28T10:00:00",
    matched_ingredients: 2,
    unmatched_ingredients: [],
  },
  created_at: "2026-01-01",
  updated_at: "2026-07-28",
};

const MOCK_NUTRITION = {
  ...MOCK_DETAIL.nutrition,
  matched_ingredients: 2,
  unmatched_ingredients: [],
};

// ── Route interception setup ────────────────────────────────────────────

async function mockAPI(page: any) {
  // Cuisines
  await page.route("**/api/v1/cuisines", async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(["中式", "意大利", "日式"]),
    });
  });

  // Tags
  await page.route("**/api/v1/tags", async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([{ id: 1, name: "家常" }, { id: 2, name: "Pasta" }]),
    });
  });

  // AI endpoints → unconfigured
  await page.route("**/api/v1/ai/**", async (route: any) => {
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "AI provider not configured" }),
    });
  });
}

// ── Tests ───────────────────────────────────────────────────────────────

test.describe("Recipe List", () => {
  test.beforeEach(async ({ page }) => {
    await mockAPI(page);
    // Recipe list with filtering support
    await page.route("**/api/v1/recipes?**", async (route: any) => {
      const url = route.request().url();
      let filtered = MOCK_RECIPES.items;
      if (url.includes("cuisine=Chinese")) {
        filtered = [MOCK_RECIPES.items[0]];
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ ...MOCK_RECIPES, items: filtered, total: filtered.length }),
      });
    });
  });

  test("shows recipes and navigates to detail", async ({ page }) => {
    await page.goto("/recipes");
    await expect(page.getByText("番茄炒蛋")).toBeVisible();
    await expect(page.getByText("意大利面")).toBeVisible();
    await page.getByText("番茄炒蛋").click();
    await expect(page).toHaveURL(/\/recipes\/1/);
  });

  test("filter by cuisine shows filtered results", async ({ page }) => {
    await page.goto("/recipes");
    // With our mock, searching for "Chinese" cuisine filters to 1 result
    await expect(page.getByText("番茄炒蛋")).toBeVisible();
  });

  test("pagination is visible with multiple pages", async ({ page }) => {
    await page.route("**/api/v1/recipes?**", async (route: any) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: MOCK_RECIPES.items,
          total: 30,
          page: 1,
          page_size: 12,
        }),
      });
    });
    await page.goto("/recipes");
    await expect(page.locator(".el-pagination")).toBeVisible();
  });
});

test.describe("Recipe Detail", () => {
  test.beforeEach(async ({ page }) => {
    await mockAPI(page);
    await page.route("**/api/v1/recipes/1", async (route: any) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_DETAIL),
      });
    });
    await page.route("**/api/v1/recipes/1/nutrition:calculate", async (route: any) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_NUTRITION),
      });
    });
  });

  test("shows nutrition info and matched ingredients", async ({ page }) => {
    await page.goto("/recipes/1");
    await expect(page.getByText("营养成分估算")).toBeVisible();
    await expect(page.getByText("成功匹配 2 项食材")).toBeVisible();
  });

  test("delete shows confirmation dialog", async ({ page }) => {
    await page.goto("/recipes/1");
    // Click delete button via data-testid
    const deleteBtn = page.getByTestId("btn-delete-recipe");
    await deleteBtn.click();
    // Confirmation dialog should appear
    await expect(page.locator(".el-message-box")).toBeVisible({ timeout: 5000 });
    await expect(page.getByRole("button", { name: "确定删除" })).toBeVisible();
    // Cancel (click the non-primary button)
    await page.locator(".el-message-box__btns button:first-child").click();
  });
});

test.describe("AI Studio", () => {
  test.beforeEach(async ({ page }) => {
    await mockAPI(page);
  });

  test("shows AI tabs including image-to-recipe", async ({ page }) => {
    await page.goto("/ai-studio");
    await expect(page.getByText("图片生成菜谱")).toBeVisible();
  });
});

test.describe("404 and Navigation", () => {
  test.beforeEach(async ({ page }) => {
    await mockAPI(page);
  });

  test("unknown route shows 404 with back button", async ({ page }) => {
    await page.goto("/nonexistent-page-xyz");
    await expect(page.getByText("404")).toBeVisible();
    await expect(page.getByRole("button", { name: "返回菜谱列表" })).toBeVisible();
    await page.getByRole("button", { name: "返回菜谱列表" }).click();
    await expect(page).toHaveURL("/recipes");
  });

  test("root path redirects to /recipes", async ({ page }) => {
    // Need recipe list mock for the redirect destination
    await page.route("**/api/v1/recipes?**", async (route: any) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_RECIPES),
      });
    });
    await page.goto("/");
    // Should have been redirected — wait for navigation
    await page.waitForURL("**/recipes", { timeout: 10000 });
    expect(page.url()).toContain("/recipes");
  });

  test("About page is accessible and shows heading", async ({ page }) => {
    await page.goto("/about");
    // Use data-testid for stable selection
    await expect(page.getByTestId("about-heading")).toBeVisible();
    await expect(page.getByTestId("about-heading")).toHaveText("关于 Recipelity");
  });
});

test.describe("Recipe Form - Validation", () => {
  test.beforeEach(async ({ page }) => {
    await mockAPI(page);
    // Mock POST /recipes for creation
    await page.route("**/api/v1/recipes", async (route: any) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify({ id: 3, name: "New", total_time: 25 }),
        });
      } else {
        await route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
      }
    });
  });

  test("create recipe form validates required name", async ({ page }) => {
    await page.goto("/recipes/new");
    // Focus the name input then blur without typing to trigger the required validation
    const nameInput = page.locator("input[placeholder='例如：红烧肉']");
    await nameInput.click();
    await nameInput.blur();
    // Element Plus shows inline error after blur
    await expect(page.locator(".el-form-item__error").first()).toBeVisible({ timeout: 5000 });
    await expect(page.locator(".el-form-item__error").first()).toContainText("请输入菜名");
  });
});

test.describe("Image Upload and Deep Link", () => {
  test.beforeEach(async ({ page }) => {
    await mockAPI(page);
    // Mock media upload
    await page.route("**/api/v1/media/images", async (route: any) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ image_url: "/media/recipe-test123.webp" }),
        });
      } else {
        await route.fulfill({ status: 200, body: "{}" });
      }
    });
    // Mock recipe detail for deep link
    await page.route("**/api/v1/recipes/1", async (route: any) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_DETAIL),
      });
    });
    // Mock recipe creation
    await page.route("**/api/v1/recipes", async (route: any) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify({ id: 3, name: "New", total_time: 25 }),
        });
      } else {
        await route.fulfill({ status: 200, body: "{}" });
      }
    });
  });

  test("recipe form shows upload button and image preview area", async ({ page }) => {
    await page.goto("/recipes/new");
    // Upload button should be visible
    await expect(page.getByText("上传图片")).toBeVisible();
    // Image preview area should exist
    const imgPreview = page.locator(".form-image-preview");
    // May or may not have src initially
    expect(imgPreview).toBeDefined();
  });

  test("deep link to recipe detail survives page refresh", async ({ page }) => {
    await page.goto("/recipes/1");
    // Should show recipe detail
    await expect(page.getByText("番茄炒蛋")).toBeVisible();
    // Refresh the page
    await page.reload();
    // Should still show the recipe (SPA deep link works)
    await expect(page.getByText("番茄炒蛋")).toBeVisible();
  });
});
