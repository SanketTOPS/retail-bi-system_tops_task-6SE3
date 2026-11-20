/**
 * src/context/AuthContext.jsx
 * ───────────────────────────
 * Global authentication state via React Context + useReducer.
 *
 * State shape:
 *   { user, token, isAuthenticated, isLoading }
 *
 * Provided values / actions:
 *   login(email, password)  — calls API, stores token, sets user
 *   register(data)          — calls API, then auto-login
 *   logout()                — clears state + localStorage, redirects /login
 *   user                    — { id, email, full_name, role }
 *   role                    — shorthand for user?.role
 *   isAuthenticated         — boolean
 *   isLoading               — true while checking stored token on mount
 *
 * Token persistence:
 *   On mount, AuthContext reads the token from localStorage and calls
 *   GET /auth/me to verify it is still valid. If valid → user is logged in.
 *   If the call fails (token expired) → user is logged out silently.
 *   This ensures page-refresh preserves the session without flashing the
 *   login screen for authenticated users.
 *
 * Auto-logout on 401:
 *   axiosInstance fires `window.dispatchEvent(new CustomEvent('auth:logout'))`
 *   on any 401 response. AuthContext listens for this event and calls logout().
 *
 * Design: Why useReducer instead of useState?
 *   Auth state has multiple fields that change together (user + token +
 *   isAuthenticated). useReducer with named actions is easier to reason about,
 *   easier to test, and prevents partial state updates (e.g., token set but
 *   isAuthenticated still false).
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useReducer,
} from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { loginApi, registerApi, getMeApi } from '@/api/auth';
import {
  TOKEN_KEY,
  USER_KEY,
  setToken,
  clearAuth,
  getToken,
} from '@/api/axiosInstance';

// ── Context ──────────────────────────────────────────────────────────────────
export const AuthContext = createContext(null);

// ── Reducer ──────────────────────────────────────────────────────────────────
const initialState = {
  user:            null,
  token:           null,
  isAuthenticated: false,
  isLoading:       true,   // true until mount check completes
};

function authReducer(state, action) {
  switch (action.type) {
    case 'AUTH_SUCCESS':
      return {
        ...state,
        user:            action.payload.user,
        token:           action.payload.token,
        isAuthenticated: true,
        isLoading:       false,
      };
    case 'LOGOUT':
      return { ...initialState, isLoading: false };
    case 'SET_LOADING':
      return { ...state, isLoading: action.payload };
    default:
      return state;
  }
}

// ── Provider ─────────────────────────────────────────────────────────────────
export function AuthProvider({ children }) {
  const [state, dispatch] = useReducer(authReducer, initialState);
  const navigate = useNavigate();

  // ── On mount: hydrate from stored token ─────────────────────────────────
  useEffect(() => {
    async function hydrateSession() {
      const storedToken = getToken();
      if (!storedToken) {
        dispatch({ type: 'SET_LOADING', payload: false });
        return;
      }
      try {
        // Verify the token is still valid by fetching the current user
        const user = await getMeApi();
        dispatch({
          type: 'AUTH_SUCCESS',
          payload: { user, token: storedToken },
        });
      } catch {
        // Token invalid or expired — clear and show login
        clearAuth();
        dispatch({ type: 'LOGOUT' });
      }
    }
    hydrateSession();
  }, []);

  // ── Listen for 401 auto-logout event from axiosInstance ─────────────────
  useEffect(() => {
    const handleForcedLogout = () => {
      dispatch({ type: 'LOGOUT' });
      toast.error('Your session expired. Please log in again.');
    };
    window.addEventListener('auth:logout', handleForcedLogout);
    return () => window.removeEventListener('auth:logout', handleForcedLogout);
  }, []);

  // ── login ────────────────────────────────────────────────────────────────
  const login = useCallback(async (email, password) => {
    const data = await loginApi({ email, password });
    // Backend returns { access_token, user } or { access_token, token_type }
    const token = data.access_token;
    // Some endpoints return user nested, some at top level
    const user  = data.user ?? { email };

    setToken(token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));

    // Fetch full user profile to get role etc.
    let fullUser = user;
    try { fullUser = await getMeApi(); } catch { /* use login response user */ }

    dispatch({ type: 'AUTH_SUCCESS', payload: { user: fullUser, token } });
    toast.success(`Welcome back, ${fullUser.full_name ?? fullUser.email}!`);
    navigate('/dashboard', { replace: true });
  }, [navigate]);

  // ── register ─────────────────────────────────────────────────────────────
  const register = useCallback(async ({ full_name, email, password }) => {
    await registerApi({ full_name, email, password });
    toast.success('Account created! Logging you in…');
    // Auto-login after registration
    await login(email, password);
  }, [login]);

  // ── logout ───────────────────────────────────────────────────────────────
  const logout = useCallback(() => {
    clearAuth();
    dispatch({ type: 'LOGOUT' });
    toast.success('Logged out successfully.');
    navigate('/login', { replace: true });
  }, [navigate]);

  const value = {
    user:            state.user,
    token:           state.token,
    role:            state.user?.role ?? null,
    isAuthenticated: state.isAuthenticated,
    isLoading:       state.isLoading,
    login,
    register,
    logout,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

// ── Hook ─────────────────────────────────────────────────────────────────────
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
