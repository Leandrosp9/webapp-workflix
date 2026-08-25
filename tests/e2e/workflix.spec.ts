import { expect, type Page, test } from "@playwright/test";

const demoPassword = "Workflix@2026";
const apiBaseUrl = process.env.PLAYWRIGHT_API_BASE_URL ?? "/api/v1";
const avatarPng = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
  "base64",
);
const cachedSessions = new Map<
  string,
  { accessToken: string; refreshToken: string }
>();

function apiUrl(path: string) {
  return `${apiBaseUrl}${path.startsWith("/") ? path : `/${path}`}`;
}

async function login(page: Page, email: string) {
  await page.goto("/login");
  const cached = cachedSessions.get(email);
  if (cached) {
    await page.evaluate(({ accessToken, refreshToken }) => {
      localStorage.setItem("workflix.access", accessToken);
      localStorage.setItem("workflix.refresh", refreshToken);
    }, cached);
    await page.goto(email.startsWith("admin@") ? "/admin" : "/app");
  } else {
    await page.getByLabel("E-mail corporativo").fill(email);
    await page.getByLabel("Senha").fill(demoPassword);
    await page.getByRole("button", { name: "Entrar na Workflix" }).click();
    await expect(page).toHaveURL(
      email.startsWith("admin@") ? /\/admin$/ : /\/app$/,
      { timeout: 15_000 },
    );
    const session = await page.evaluate(() => ({
      accessToken: localStorage.getItem("workflix.access") ?? "",
      refreshToken: localStorage.getItem("workflix.refresh") ?? "",
    }));
    expect(session.accessToken).not.toBe("");
    expect(session.refreshToken).not.toBe("");
    cachedSessions.set(email, session);
  }
  await expect(page).toHaveURL(
    email.startsWith("admin@") ? /\/admin$/ : /\/app$/,
    { timeout: 15_000 },
  );
}

async function logout(page: Page) {
  await page.getByRole("button", { name: /Abrir menu da conta de/ }).click();
  await page.getByRole("button", { name: "Sair da conta" }).click();
}

async function expectNoHorizontalOverflow(page: Page) {
  const dimensions = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    content: document.documentElement.scrollWidth,
  }));
  expect(dimensions.content).toBeLessThanOrEqual(dimensions.viewport + 1);
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
  await expect(page.getByText("Impulso do dia")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Ranking da equipe" }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: /Começar agora|Continuar/ })
    .first()
    .click();

  await expect(page).toHaveURL(/\/app\/training\//);
  await expect(
    page.getByRole("button", { name: "Avançar para avaliação" }).first(),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Voltar aos treinamentos" }),
  ).toHaveAttribute("href", "/app/catalog");
  await page
    .getByRole("button", { name: "Avançar para avaliação" })
    .first()
    .click();

  await expect(page).toHaveURL(/\/app\/training\/[^/]+\/quiz$/);
  await page.getByRole("link", { name: "Sair da avaliação" }).click();
  await expect(
    page.getByRole("button", { name: "Continuar na avaliação" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Continuar na avaliação" }).click();
  await expect(page).toHaveURL(/\/app\/training\/[^/]+\/quiz$/);

  const correctAnswers = [
    "Confirmar o pedido por um canal oficial antes de agir.",
    "Usar senha única e autenticação multifator.",
  ];
  for (const answer of correctAnswers) {
    await page.getByRole("button", { name: answer }).click();
    const finish = page.getByRole("button", { name: "Finalizar avaliação" });
    if (await finish.isVisible()) {
      await finish.click();
      break;
    }
    await page.getByRole("button", { name: /Próxima/ }).click();
  }

  await expect(page.getByText("Resultado da avaliação")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Muito bem!" })).toBeVisible();
  await page.getByRole("link", { name: "Ver certificado" }).click();
  await expect(page).toHaveURL(/\/app\/certificates$/);
  await expect(
    page.getByText("Certificado de treinamento").first(),
  ).toBeVisible();
  const certificate = page.locator(".certificate-card").first();
  await expect(
    certificate.getByRole("link", {
      name: "Compartilhar certificado no WhatsApp",
    }),
  ).toHaveAttribute("href", /^https:\/\/wa\.me\/\?text=/);
  await expect(
    certificate.getByRole("link", {
      name: "Compartilhar certificado no LinkedIn",
    }),
  ).toHaveAttribute(
    "href",
    /^https:\/\/www\.linkedin\.com\/sharing\/share-offsite\/\?url=/,
  );
  const certificateCode = (
    await certificate.locator(".certificate-code").textContent()
  )?.trim();
  expect(certificateCode).toBeTruthy();

  await page.goto(`/verify/${encodeURIComponent(certificateCode ?? "")}`);
  await expect(page.getByText("Certificado autêntico")).toBeVisible();
  await expect(page.getByText("CPF ***.000.001-**")).toBeVisible();
});

test("colaborador assiste a um vídeo demonstrativo no treinamento", async ({
  page,
}) => {
  await login(page, "employee@workflix.demo");
  await page.goto("/app/catalog");

  await page
    .getByRole("link")
    .filter({ hasText: "LGPD na prática: dados com responsabilidade" })
    .first()
    .click();

  const video = page.getByTitle(
    "Vídeo do treinamento LGPD na prática: dados com responsabilidade",
  );
  await expect(video).toBeVisible();
  await expect(video).toHaveAttribute(
    "src",
    "https://www.youtube-nocookie.com/embed/jVuQjczLvRI?rel=0",
  );
  await expect(video).toHaveAttribute(
    "sandbox",
    "allow-scripts allow-same-origin allow-presentation",
  );
  await expect(
    page.getByRole("heading", { name: "Assista dentro do Workflix" }),
  ).toBeVisible();
  await expect(page.locator(".video-player a")).toHaveCount(0);
});

test("colaborador retoma o treinamento na última posição de leitura", async ({
  page,
}) => {
  await login(page, "employee@workflix.demo");
  await page.goto("/app/catalog");

  const trainingCard = page
    .getByRole("link")
    .filter({ hasText: "Liderança para ambientes híbridos" })
    .first();
  await trainingCard.click();

  const trainingId = page.url().split("/").at(-1) ?? "";
  const resumeStorageKey = `workflix.training.resume.${trainingId}`;
  await page.locator(".article-content").evaluate((element) =>
    element.scrollIntoView({
      block: "center",
    }),
  );
  await expect
    .poll(() =>
      page.evaluate((storageKey) => {
        return Number(window.localStorage.getItem(storageKey) ?? 0);
      }, resumeStorageKey),
    )
    .toBeGreaterThan(0);
  const savedPosition = await page.evaluate((storageKey) => {
    return Number(window.localStorage.getItem(storageKey) ?? 0);
  }, resumeStorageKey);

  await page.goto("/app/catalog");
  await trainingCard.click();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.getByRole("button", { name: "Continuar de onde parou" }).click();

  await expect
    .poll(() => page.evaluate(() => window.scrollY))
    .toBeGreaterThan(savedPosition - 30);
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

  const accountMenu = page.getByRole("button", {
    name: "Abrir menu da conta de Marina Costa",
  });
  await expect(accountMenu).toHaveAttribute("aria-expanded", "false");
  await accountMenu.click();
  await expect(page.getByText("admin@workflix.demo")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Sair da conta" }),
  ).toBeVisible();

  await page.getByRole("link", { name: "Treinamentos", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Treinamentos" }),
  ).toBeVisible();

  await page.getByRole("link", { name: "Colaboradores", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Colaboradores" }),
  ).toBeVisible();
  await expect(page.getByText("employee@workflix.demo")).toBeVisible();

  const validationEmail = "rafael.mendes@workflix.demo";
  const validationEmployee = page
    .locator(".people-table tbody tr")
    .filter({ hasText: validationEmail });
  if ((await validationEmployee.count()) === 0) {
    await page.getByRole("button", { name: "Novo colaborador" }).click();
    await page.getByLabel("Nome completo").fill("Rafael Mendes");
    await page.getByLabel("CPF").fill("900.000.009-22");
    await page.getByLabel("E-mail corporativo").fill(validationEmail);
    await page.getByRole("button", { name: "Criar acesso" }).click();
    await expect(
      page.getByText("Colaborador adicionado e acesso liberado."),
    ).toBeVisible();
  }

  await validationEmployee.getByTitle("Editar colaborador").click();
  await page.getByLabel("Nome completo").fill("Rafael Mendes da Silva");
  const cpf = page.getByLabel("CPF");
  if ((await cpf.inputValue()) === "") {
    await cpf.fill("900.000.009-22");
  }
  await page.getByLabel("Foto do colaborador").setInputFiles({
    name: "rafael.png",
    mimeType: "image/png",
    buffer: avatarPng,
  });
  await page.getByRole("button", { name: "Salvar alterações" }).click();
  await expect(
    page.getByText("Dados de Rafael Mendes da Silva atualizados."),
  ).toBeVisible();
  await expect(
    validationEmployee.getByAltText("Foto de Rafael Mendes da Silva"),
  ).toBeVisible();

  if (
    await validationEmployee.getByText("Inativo", { exact: true }).isVisible()
  ) {
    await validationEmployee.getByTitle("Ativar acesso").click();
    await page.getByRole("button", { name: "Confirmar ativação" }).click();
    await expect(
      validationEmployee.getByText("Ativo", { exact: true }),
    ).toBeVisible();
  }
  await validationEmployee.getByTitle("Inativar acesso").click();
  await page.getByRole("button", { name: "Confirmar inativação" }).click();
  await expect(
    validationEmployee.getByText("Inativo", { exact: true }),
  ).toBeVisible();

  await page.getByRole("link", { name: "Trilhas", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Trilhas" })).toBeVisible();
  const validationPath = "Integração e Segurança Operacional";
  const pathAlreadyExists =
    (await page
      .locator(".path-list")
      .getByText(validationPath, { exact: true })
      .count()) > 0;
  await page.getByRole("button", { name: "Nova trilha" }).click();
  const pathName = page.getByLabel("Nome", { exact: true });
  await expect(pathName).toBeFocused();
  if (!pathAlreadyExists) {
    await pathName.fill(validationPath);
    await page
      .getByLabel("Descrição")
      .fill(
        "Jornada de validação para integração segura de novos colaboradores.",
      );
    await page.getByRole("button", { name: "Criar rascunho" }).click();
    await expect(page.getByText("Trilha criada como rascunho.")).toBeVisible();
  }

  await page.getByRole("link", { name: "Relatórios", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Relatórios e analytics" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Progresso CSV" }),
  ).toBeVisible();
});

test("fluxo demo cria conteúdo com IA, publica, atribui e confirma conclusão", async ({
  page,
}) => {
  await page.route("**/api/v1/ai/generate-training", async (route) => {
    await route.fulfill({
      json: {
        draft: {
          title: "Proteção de dados em projetos digitais",
          description:
            "Decisões práticas para reduzir riscos no uso de dados de clientes.",
          content:
            "# Proteção de dados desde o início\n\nMapeie a finalidade, limite a coleta e use somente canais aprovados. " +
            "Registre decisões, valide acessos e comunique incidentes imediatamente pelo canal oficial.",
          estimated_minutes: 16,
        },
        generation: {
          provider: "gemini",
          model: "gemini-demo",
          fallback_used: false,
        },
      },
    });
  });
  await page.route("**/api/v1/ai/generate-quiz", async (route) => {
    await route.fulfill({
      json: {
        draft: {
          passing_score: 70,
          questions: [
            {
              text: "Qual princípio deve orientar a coleta de dados?",
              explanation:
                "A coleta deve se limitar ao necessário para a finalidade informada.",
              options: [
                { text: "Coletar somente o necessário.", is_correct: true },
                { text: "Coletar tudo para uso futuro.", is_correct: false },
              ],
            },
            {
              text: "Como agir diante de um possível incidente?",
              explanation:
                "O canal oficial preserva evidências e acelera a resposta adequada.",
              options: [
                {
                  text: "Interromper e comunicar pelo canal oficial.",
                  is_correct: true,
                },
                {
                  text: "Investigar sozinho antes de avisar.",
                  is_correct: false,
                },
              ],
            },
          ],
        },
        generation: {
          provider: "gemini",
          model: "gemini-demo",
          fallback_used: false,
        },
      },
    });
  });

  await login(page, "admin@workflix.demo");
  await expect(page).toHaveURL(/\/admin$/);
  const adminToken = await page.evaluate(() =>
    localStorage.getItem("workflix.access"),
  );
  expect(adminToken).toBeTruthy();
  const adminHeaders = { Authorization: `Bearer ${adminToken}` };
  let trainingId = "";

  try {
    await page.getByRole("link", { name: "Novo treinamento" }).click();
    await page.getByLabel("Título").fill("Proteção de dados em projetos");
    await page
      .getByLabel("Descrição")
      .fill(
        "Boas práticas para equipes que trabalham com informações de clientes.",
      );
    await page.getByRole("button", { name: "Criar com Gemini" }).click();
    await expect(page.getByText("Rascunho gerado.")).toBeVisible();
    await expect(page.getByLabel("Conteúdo")).toHaveValue(
      /Proteção de dados desde o início/,
    );

    await page.getByRole("button", { name: "Salvar", exact: true }).click();
    await expect(page).toHaveURL(/\/admin\/trainings\/[0-9a-f-]+$/);
    trainingId = page.url().split("/").at(-1) ?? "";
    expect(trainingId).toBeTruthy();

    await page.getByRole("button", { name: "Gerar 5 questões" }).click();
    await expect(page.getByPlaceholder("Enunciado").first()).toHaveValue(
      "Qual princípio deve orientar a coleta de dados?",
    );
    await page.getByRole("button", { name: "Salvar avaliação" }).click();
    await expect(page.getByText("Avaliação salva.")).toBeVisible();

    await page.getByLabel("Status").selectOption("PUBLISHED");
    await page.getByRole("button", { name: "Salvar", exact: true }).click();
    await expect(page.getByText("Treinamento salvo.")).toBeVisible();

    const employeeChoice = page
      .locator(".employee-selector label")
      .filter({ hasText: "employee@workflix.demo" });
    await employeeChoice.getByRole("checkbox").check();
    await page.getByRole("button", { name: "Atribuir treinamento" }).click();
    await expect(page.getByText(/1 novas atribuições/)).toBeVisible();

    await logout(page);
    await login(page, "employee@workflix.demo");
    await page.goto(`/app/training/${trainingId}`);
    await expect(
      page
        .getByRole("heading", {
          name: "Proteção de dados em projetos digitais",
        })
        .first(),
    ).toBeVisible();
    await page
      .getByRole("button", { name: "Avançar para avaliação" })
      .first()
      .click();
    await page.locator(".quiz-options button").first().click();
    await page.getByRole("button", { name: /Próxima/ }).click();
    await page.locator(".quiz-options button").first().click();
    await page.getByRole("button", { name: "Finalizar avaliação" }).click();
    await expect(
      page.getByRole("heading", { name: "Muito bem!" }),
    ).toBeVisible();
    await page.getByRole("link", { name: "Ver certificado" }).click();
    await expect(
      page
        .getByRole("heading", {
          name: "Proteção de dados em projetos digitais",
        })
        .first(),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Privacidade na prática" }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Baixar PDF" }).first(),
    ).toBeVisible();

    await logout(page);
    await login(page, "admin@workflix.demo");
    await page.goto("/admin/reports");
    const trainingRow = page.getByRole("row").filter({
      hasText: "Proteção de dados em projetos digitais",
    });
    await expect(trainingRow).toContainText("100%");
  } finally {
    if (trainingId) {
      const removed = await page.request.delete(
        apiUrl(`/trainings/${trainingId}`),
        {
          headers: adminHeaders,
        },
      );
      expect(removed.status()).toBe(204);
    }
  }
});

test("trilha concluída exibe certificado verificável ao colaborador", async ({
  page,
}) => {
  await login(page, "employee@workflix.demo");
  await page.goto("/app/paths");
  await expect(
    page.getByRole("heading", { name: "Minhas trilhas" }),
  ).toBeVisible();
  await page.getByRole("link", { name: /Privacidade na prática/ }).click();
  await expect(page.getByText("Certificado emitido")).toBeVisible();

  await page.getByRole("link", { name: "Certificados", exact: true }).click();
  const certificate = page
    .getByRole("article")
    .filter({ hasText: "Privacidade na prática" });
  await expect(
    certificate.getByRole("heading", { name: "Privacidade na prática" }),
  ).toBeVisible();
  await expect(
    certificate.getByRole("button", { name: "Baixar PDF" }),
  ).toBeVisible();
});

test("administrador versiona PDF e acompanha a extração", async ({ page }) => {
  await login(page, "admin@workflix.demo");
  await expect(page).toHaveURL(/\/admin$/);
  const token = await page.evaluate(() =>
    localStorage.getItem("workflix.access"),
  );
  expect(token).toBeTruthy();
  const headers = { Authorization: `Bearer ${token}` };
  const created = await page.request.post(apiUrl("/trainings"), {
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
            apiUrl(`/trainings/${training.id}/document`),
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
            apiUrl(`/trainings/${training.id}/document`),
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
      apiUrl(`/trainings/${training.id}`),
      { headers },
    );
    expect(removed.status()).toBe(204);
  }
});

test("colaborador registra ciência da versão atual do PDF", async ({
  page,
}) => {
  await login(page, "employee@workflix.demo");
  await expect(page).toHaveURL(/\/app$/);
  const trainingId = "10000000-0000-4000-8000-000000000001";
  const documentId = "20000000-0000-4000-8000-000000000001";
  const versionId = "30000000-0000-4000-8000-000000000001";
  const acknowledgementId = "40000000-0000-4000-8000-000000000001";
  const checksum = "a".repeat(64);
  let postedVersion = "";

  await page.route(
    `**/api/v1/employee/trainings/${trainingId}`,
    async (route) => {
      await route.fulfill({
        json: {
          id: trainingId,
          company_id: "50000000-0000-4000-8000-000000000001",
          title: "Política de segurança da informação",
          description: "Documento obrigatório para todos os colaboradores.",
          type: "PDF",
          thumbnail_url: null,
          content: "",
          video_url: null,
          has_pdf: true,
          estimated_minutes: 8,
          status: "PUBLISHED",
          created_at: "2026-08-22T12:00:00Z",
          updated_at: "2026-08-22T12:00:00Z",
          progress_percent: 0,
          assigned_at: "2026-08-22T12:00:00Z",
          due_date: null,
          has_quiz: false,
        },
      });
    },
  );
  await page.route(
    `**/api/v1/trainings/${trainingId}/document`,
    async (route) => {
      await route.fulfill({
        json: {
          id: versionId,
          document_id: documentId,
          version_number: 3,
          original_filename: "politica-seguranca.pdf",
          content_type: "application/pdf",
          size_bytes: 2048,
          checksum,
          status: "READY",
          page_count: 4,
          ocr_page_count: 2,
          chunk_count: 8,
          error_code: null,
          created_at: "2026-08-22T12:00:00Z",
          updated_at: "2026-08-22T12:00:00Z",
          processed_at: "2026-08-22T12:01:00Z",
        },
      });
    },
  );
  await page.route(
    `**/api/v1/employee/trainings/${trainingId}/acknowledgement`,
    async (route) => {
      const acknowledged = route.request().method() === "POST";
      if (acknowledged) {
        postedVersion = (
          route.request().postDataJSON() as { document_version_id: string }
        ).document_version_id;
      }
      await route.fulfill({
        json: {
          document_version_id: versionId,
          version_number: 3,
          document_checksum: checksum,
          attestation: "Confirmo que li e compreendi esta versão do documento.",
          acknowledged,
          acknowledgement: acknowledged
            ? {
                id: acknowledgementId,
                training_id: trainingId,
                document_id: documentId,
                document_version_id: versionId,
                user_id: "60000000-0000-4000-8000-000000000001",
                user_email: "employee@workflix.demo",
                user_full_name: "Lucas Andrade",
                document_title: "Política de segurança da informação",
                original_filename: "politica-seguranca.pdf",
                version_number: 3,
                document_checksum: checksum,
                attestation:
                  "Confirmo que li e compreendi esta versão do documento.",
                acknowledged_at: "2026-08-22T12:05:00Z",
              }
            : null,
        },
      });
    },
  );

  await page.goto(`/app/training/${trainingId}`);
  await expect(page.getByText("Ciência do documento")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Versão 3" })).toBeVisible();
  await page.getByRole("button", { name: "Li e estou ciente" }).click();
  await expect(
    page.getByRole("button", { name: "Ciência registrada" }),
  ).toBeVisible();
  await expect(page.getByText(/SHA-256 aaaaaaaaaaaa/)).toBeVisible();
  expect(postedVersion).toBe(versionId);
});

test("telas principais permanecem responsivas em desktop, notebook, tablet e mobile", async ({
  page,
}) => {
  test.setTimeout(120_000);
  const viewports = [
    { width: 1920, height: 1080 },
    { width: 1366, height: 768 },
    { width: 820, height: 1180 },
    { width: 390, height: 844 },
  ];

  for (const viewport of viewports) {
    await page.setViewportSize(viewport);
    await page.goto("/login");
    await expect(
      page.getByRole("heading", { name: "Acesse sua conta" }),
    ).toBeVisible();
    await expectNoHorizontalOverflow(page);
  }

  await login(page, "employee@workflix.demo");
  const trainingHref = await page
    .getByRole("link", { name: /Começar agora|Continuar/ })
    .first()
    .getAttribute("href");
  expect(trainingHref).toBeTruthy();
  for (const viewport of viewports) {
    await page.setViewportSize(viewport);
    for (const path of ["/app", "/app/catalog", trainingHref!]) {
      await page.goto(path);
      await expect(page.locator("main.page-content")).toBeVisible();
      await expectNoHorizontalOverflow(page);
    }
    const menu = page.getByRole("button", { name: "Abrir menu", exact: true });
    if (viewport.width <= 980) await expect(menu).toBeVisible();
    else await expect(menu).toBeHidden();
  }

  await page.evaluate(() => localStorage.clear());
  await login(page, "admin@workflix.demo");
  for (const viewport of viewports) {
    await page.setViewportSize(viewport);
    for (const path of ["/admin", "/admin/trainings", "/admin/reports"]) {
      await page.goto(path);
      await expect(page.locator("main.page-content")).toBeVisible();
      await expectNoHorizontalOverflow(page);
    }
  }
});
