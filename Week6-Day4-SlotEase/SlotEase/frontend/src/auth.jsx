import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api, getToken, setToken } from './api'

const AuthCtx = createContext(null)

export function AuthProvider({ children }) {
  const [state, setState] = useState({ loading: !!getToken(), user: null, business: null })

  const refresh = useCallback(async () => {
    if (!getToken()) { setState({ loading: false, user: null, business: null }); return }
    try {
      const me = await api('/auth/me')
      setState({ loading: false, ...me })
    } catch {
      setToken(null)
      setState({ loading: false, user: null, business: null })
    }
  }, [])

  useEffect(() => { refresh() }, [refresh])
  useEffect(() => {
    const onLogout = () => setState({ loading: false, user: null, business: null })
    window.addEventListener('slotease:logout', onLogout)
    return () => window.removeEventListener('slotease:logout', onLogout)
  }, [])

  const acceptAuth = (data) => {
    setToken(data.access_token)
    setState({ loading: false, user: data.user, business: data.business })
  }
  const login = async (email, password) => acceptAuth(await api('/auth/login', { method: 'POST', body: { email, password }, auth: false }))
  const register = async (body) => acceptAuth(await api('/auth/register', { method: 'POST', body, auth: false }))
  const logout = () => { setToken(null); setState({ loading: false, user: null, business: null }) }
  const setBusiness = (business) => setState((s) => ({ ...s, business }))

  return <AuthCtx.Provider value={{ ...state, login, register, logout, refresh, setBusiness }}>{children}</AuthCtx.Provider>
}

export const useAuth = () => useContext(AuthCtx)
