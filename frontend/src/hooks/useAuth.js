/**
 * src/hooks/useAuth.js
 * ─────────────────────
 * Re-export of useAuth from AuthContext for convenience.
 * Consumers import from '@/hooks/useAuth' (intuitive hook location)
 * rather than the deeper '@/context/AuthContext'.
 */
export { useAuth } from '@/context/AuthContext';
