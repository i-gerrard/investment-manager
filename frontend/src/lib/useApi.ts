"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";

interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useGet<T>(path: string, deps: unknown[] = []): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const mounted = useRef(true);

  const fetcher = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.get<T>(path);
      if (mounted.current) {
        setData(result);
        setLoading(false);
      }
    } catch (err: any) {
      if (mounted.current) {
        setError(err instanceof ApiError ? err.message : "Request failed");
        setLoading(false);
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, ...deps]);

  useEffect(() => {
    mounted.current = true;
    fetcher();
    return () => { mounted.current = false; };
  }, [fetcher]);

  return { data, loading, error, refetch: fetcher };
}

export function usePost<T>(path: string) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const execute = useCallback(async (body?: unknown): Promise<T | null> => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.post<T>(path, body);
      setLoading(false);
      return result;
    } catch (err: any) {
      setError(err instanceof ApiError ? err.message : "Request failed");
      setLoading(false);
      return null;
    }
  }, [path]);

  return { execute, loading, error };
}
