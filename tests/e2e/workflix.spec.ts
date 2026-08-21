import { expect, type Page, test } from "@playwright/test";

const demoPassword = "Workflix@2026";

async function login(page: Page, email: string) {
  await page.goto("/login");
  await page.getByLabel("E-mail corporativo").fill(email);
  await page.getByLabel("Senha").fill(demoPassword);
  await page.getByRole("button", { name: "Entrar na Workflix" }).click();
}

function makeTextPdf(text: string): Buffer {
  const stream = `BT\n/F1 12 Tf\n72 720 Td\n(${text.replace(/[()\\]/g, " ")}) Tj\nET\n`;
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
    `<< /Length ${Buffer.byteLength(stream)} >>\nstream\n${stream}endstream`,
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
  ];
  let pdf = "%PDF-1.4\n";
  const offsets = [0];
  objects.forEach((object, index) => {
    offsets.push(Buffer.byteLength(pdf));
    pdf += `${index + 1} 0 obj\n${object}\nendobj\n`;
  });
  const xrefOffset = Buffer.byteLength(pdf);
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  pdf += offsets
    .slice(1)
    .map((offset) => `${offset.toString().padStart(10, "0")} 00000 n \n`)
    .join("");
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF\n`;
  return Buffer.from(pdf);
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

test("administrador versiona PDF e acompanha a extração", async ({ page }) => {
  await login(page, "admin@workflix.demo");
  await expect(page).toHaveURL(/\/admin$/);
  const token = await page.evaluate(() =>
    localStorage.getItem("workflix.access"),
  );
  expect(token).toBeTruthy();
  const headers = { Authorization: `Bearer ${token}` };
  const created = await page.request.post("/api/v1/trainings", {
    headers,
    data: {
      title: "Playwright PDF temporário",
      description: "Valida versionamento e extração no navegador.",
      type: "PDF",
      content: "",
      estimated_minutes: 5,
      status: "DRAFT",
    },
  });
  expect(created.ok()).toBeTruthy();
  const training = (await created.json()) as { id: string };

  try {
    await page.goto(`/admin/trainings/${training.id}`);
    await page.locator('input[type="file"]').setInputFiles({
      name: "politica.pdf",
      mimeType: "application/pdf",
      buffer: makeTextPdf("Comunique incidentes ao time de seguranca."),
    });

    await expect(
      page.getByText("Versão 1 enviada. Extração iniciada."),
    ).toBeVisible();
    let documentStatus = "UPLOADED";
    await expect
      .poll(
        async () => {
          const response = await page.request.get(
            `/api/v1/trainings/${training.id}/document`,
            { headers },
          );
          documentStatus = (await response.json()).status as string;
          return documentStatus;
        },
        { timeout: 15_000 },
      )
      .toMatch(/^(EXTRACTED|INDEXING|READY|FAILED)$/);
    await page.waitForTimeout(2_000);
    let documentVersion = {
      status: documentStatus,
      page_count: 0,
      chunk_count: 0,
    };
    await expect
      .poll(
        async () => {
          const response = await page.request.get(
            `/api/v1/trainings/${training.id}/document`,
            { headers },
          );
          documentVersion = await response.json();
          return documentVersion.status;
        },
        { timeout: 60_000 },
      )
      .toMatch(/^(EXTRACTED|READY|FAILED)$/);
    expect(documentVersion.status).not.toBe("FAILED");
    await expect(
      page.getByText(
        documentVersion.status === "READY"
          ? "Pronto para perguntas"
          : "Texto extraído",
      ),
    ).toBeVisible({ timeout: 15_000 });
    await expect(
      page.getByText(
        `${documentVersion.page_count} páginas · ${documentVersion.chunk_count} trechos indexados`,
      ),
    ).toBeVisible();
  } finally {
    const removed = await page.request.delete(
      `/api/v1/trainings/${training.id}`,
      { headers },
    );
    expect(removed.status()).toBe(204);
  }
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
