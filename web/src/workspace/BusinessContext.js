import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import * as businessesApi from "../api/businesses";
import { useAuth } from "../auth/AuthContext";

const ACTIVE_KEY = "sd_active_business";

const BusinessContext = createContext(null);

export function BusinessProvider({ children }) {
  const { token } = useAuth();
  const [businesses, setBusinesses] = useState([]);
  const [activeId, setActiveId] = useState(() => localStorage.getItem(ACTIVE_KEY));
  const [ready, setReady] = useState(false);

  const selectBusiness = useCallback((businessId) => {
    setActiveId(businessId);
    if (businessId) {
      localStorage.setItem(ACTIVE_KEY, businessId);
    } else {
      localStorage.removeItem(ACTIVE_KEY);
    }
  }, []);

  const refresh = useCallback(async () => {
    const items = await businessesApi.listBusinesses(token);
    setBusinesses(items);
    return items;
  }, [token]);

  useEffect(() => {
    let cancelled = false;

    refresh()
      .then((items) => {
        if (cancelled) {
          return;
        }
        setActiveId((current) => {
          if (current && items.some((item) => item.id === current)) {
            return current;
          }
          const nextId = items[0]?.id ?? null;
          if (nextId) {
            localStorage.setItem(ACTIVE_KEY, nextId);
          } else {
            localStorage.removeItem(ACTIVE_KEY);
          }
          return nextId;
        });
      })
      .finally(() => {
        if (!cancelled) {
          setReady(true);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [refresh]);

  const createBusiness = useCallback(
    async (payload) => {
      const created = await businessesApi.createBusiness(token, payload);
      setBusinesses((current) =>
        [...current, created].sort((a, b) => a.name.localeCompare(b.name))
      );
      selectBusiness(created.id);
      return created;
    },
    [token, selectBusiness]
  );

  const updateBusiness = useCallback(
    async (businessId, payload) => {
      const updated = await businessesApi.updateBusiness(token, businessId, payload);
      setBusinesses((current) =>
        current
          .map((item) => (item.id === updated.id ? updated : item))
          .sort((a, b) => a.name.localeCompare(b.name))
      );
      return updated;
    },
    [token]
  );

  const deleteBusiness = useCallback(
    async (businessId) => {
      await businessesApi.deleteBusiness(token, businessId);
      setBusinesses((current) => {
        const remaining = current.filter((item) => item.id !== businessId);
        setActiveId((currentId) => {
          if (currentId !== businessId) {
            return currentId;
          }
          const nextId = remaining[0]?.id ?? null;
          if (nextId) {
            localStorage.setItem(ACTIVE_KEY, nextId);
          } else {
            localStorage.removeItem(ACTIVE_KEY);
          }
          return nextId;
        });
        return remaining;
      });
    },
    [token]
  );

  const activeBusiness = useMemo(
    () => businesses.find((item) => item.id === activeId) ?? null,
    [businesses, activeId]
  );

  const value = useMemo(
    () => ({
      ready,
      businesses,
      activeBusiness,
      selectBusiness,
      createBusiness,
      updateBusiness,
      deleteBusiness,
    }),
    [
      ready,
      businesses,
      activeBusiness,
      selectBusiness,
      createBusiness,
      updateBusiness,
      deleteBusiness,
    ]
  );

  return <BusinessContext.Provider value={value}>{children}</BusinessContext.Provider>;
}

export function useBusinesses() {
  const context = useContext(BusinessContext);
  if (!context) {
    throw new Error("useBusinesses must be used within BusinessProvider");
  }
  return context;
}
