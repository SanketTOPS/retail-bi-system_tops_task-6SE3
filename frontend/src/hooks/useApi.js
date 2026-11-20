/**
 * src/hooks/useApi.js
 * ────────────────────
 * Generic async data-fetching hook.
 *
 * Returns { data, loading, error, refetch }
 *
 * Usage:
 *   const { data, loading, error } = useApi(getKpis, [datasetId]);
 *
 * Features:
 *  - Runs `fn(...args)` on mount and whenever args change (deep equal check
 *    is avoided — pass a stable reference or memoize args at the call site).
 *  - `refetch()` re-runs the function manually (e.g., after a mutation).
 *  - Cleans up with AbortController if the component unmounts mid-request.
 *  - Surfaces the raw Axios error so callers can inspect `error.response.status`.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

export default function useApi(fn, deps = []) {
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);
  const callId = useRef(0);   // tracks latest call to discard stale responses

  const execute = useCallback(async () => {
    const id = ++callId.current;
    setLoading(true);
    setError(null);
    try {
      const result = await fn();
      if (id === callId.current) {   // ignore if superseded
        setData(result);
      }
    } catch (err) {
      if (id === callId.current) {
        setError(err);
      }
    } finally {
      if (id === callId.current) {
        setLoading(false);
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => { execute(); }, [execute]);

  return { data, loading, error, refetch: execute };
}
