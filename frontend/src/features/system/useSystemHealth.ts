import { useQuery } from "@tanstack/react-query";

import { getSystemHealth } from "./api";

export function useSystemHealth() {
  return useQuery({
    queryKey: ["system", "health"],
    queryFn: getSystemHealth,
    refetchInterval: 30_000,
  });
}
