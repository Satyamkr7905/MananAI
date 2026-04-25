import { useCallback, useEffect, useState } from "react";
import toast from "react-hot-toast";

// useApi — tiny async data hook that also toasts errors.
// usage: const { data, loading, error, refetch } = useApi(getStats);
// we don't pull in SWR/React-Query because this app only has a few
// endpoints. if things grow, swap this one file out for SWR.
export const useApi = (fn, { deps = [], skip = false, onSuccess } = {}) => {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(!skip);

  const execute = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fn();
      setData(res);
      if (onSuccess) onSuccess(res);
      return res;
    } catch (err) {
      setError(err);
      toast.error(err?.message || "Something went wrong.");
      throw err;
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fn, onSuccess]);

  useEffect(() => {
    if (skip) return;
    execute();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, loading, error, refetch: execute };
};
