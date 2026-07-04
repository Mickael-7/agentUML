import { useState, useEffect, useCallback } from "react";
import type { ConfigResponse } from "@/lib/types";
import { getConfig, updateConfig } from "@/lib/api";

export function useConfig() {
  const [config, setConfig] = useState<ConfigResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchConfig = useCallback(async () => {
    try {
      const data = await getConfig();
      setConfig(data);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  const saveConfig = useCallback(async (updates: { provider?: string; model?: string; temperature?: number }) => {
    const data = await updateConfig(updates);
    setConfig(data);
    return data;
  }, []);

  return { config, loading, saveConfig, refetch: fetchConfig };
}
