import { z } from "zod";

import { getJson } from "../../services/http";

const systemHealthSchema = z.object({
  status: z.literal("healthy"),
  service: z.string(),
  version: z.string(),
  environment: z.string(),
});

export type SystemHealth = z.infer<typeof systemHealthSchema>;

export async function getSystemHealth(): Promise<SystemHealth> {
  const payload = await getJson("/system/health");
  return systemHealthSchema.parse(payload);
}
