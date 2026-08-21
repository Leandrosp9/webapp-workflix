import { expect, type Page, test } from "@playwright/test";

const demoPassword = "Workflix@2026";

async function login(page: Page, email: string) {
  await page.goto("/login");
  await page.getByLabel("E-mail corporativo").fill(email);
  await page.getByLabel("Senha").fill(demoPassword);
  await page.getByRole("button", { name: "Entrar na Workflix" }).click();
}

test("colaborador conclui o fluxo de aprendizagem e avaliação", async ({
  page,
}) => {
  await login(page, "employee@workflix.demo");

  await expect(page).toHaveURL(/\/app$/);
  await expect(
    page.getByRole("heading", { name: /O que vamos aprender hoje/ }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: /Começar agora|Continuar/ })
    .first()
    .click();

  await expect(page).toHaveURL(/\/app\/training\//);
  await expect(
    page.getByRole("link", { name: "Fazer avaliação" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Fazer avaliação" }).click();

  for (let question = 0; question < 10; question += 1) {
    await page.locator(".quiz-options button").first().click();
    const finish = page.getByRole("button", { name: "Finalizar avaliação" });
    if (await finish.isVisible()) {
      await finish.click();
      break;
    }
    await page.getByRole("button", { name: /Próxima/ }).click();
  }

  await expect(page.getByText("Resultado da avaliação")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: /Muito bem|Vamos tentar mais uma vez/ }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: /Voltar ao início/ }),
  ).toBeVisible();
});

test("administrador consulta indicadores, treinamentos e colaboradores", async ({
  page,
}) => {
  await login(page, "admin@workflix.demo");

  await expect(page).toHaveURL(/\/admin$/);
  await expect(
    page.getByRole("heading", { name: "Visão geral" }),
  ).toBeVisible();
  await expect(page.getByText("Treinamentos recentes")).toBeVisible();

  await page.getByRole("link", { name: "Treinamentos", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Treinamentos" }),
  ).toBeVisible();

  await page.getByRole("link", { name: "Colaboradores", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Colaboradores" }),
  ).toBeVisible();
  await expect(page.getByText("employee@workflix.demo")).toBeVisible();
});

test("experiência do colaborador não cria overflow horizontal no celular", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page, "employee@workflix.demo");

  await expect(
    page.getByRole("heading", { name: /O que vamos aprender hoje/ }),
  ).toBeVisible();
  const dimensions = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    content: document.documentElement.scrollWidth,
  }));
  expect(dimensions.content).toBeLessThanOrEqual(dimensions.viewport);
});
