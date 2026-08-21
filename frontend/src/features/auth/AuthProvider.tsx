import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { PropsWithChildren } from "react";

import { api, loginRequest, sessionTokens } from "../../services/http";
import type { User } from "../../types/api";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    if (!sessionTokens.refresh()) {
      setLoading(false);
      return;
    }
    void api<User>("/auth/me")
      .then((current) => {
        if (active) setUser(current);
      })
      .catch(() => sessionTokens.clear())
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      login: async (email, password) => {
        const response = await loginRequest(email, password);
        sessionTokens.save(response);
        setUser(response.user);
        return response.user;
      },
      logout: async () => {
        const refreshToken = sessionTokens.refresh();
        try {
          if (refreshToken) {
            await api<void>("/auth/logout", {
              method: "POST",
              body: JSON.stringify({ refresh_token: refreshToken }),
            });
          }
        } finally {
          sessionTokens.clear();
          setUser(null);
        }
      },
    }),
    [loading, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
