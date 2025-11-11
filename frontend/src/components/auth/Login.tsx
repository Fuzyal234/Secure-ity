import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api, User } from '@/lib/api'
import { useToast } from '@/components/ui/use-toast'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Lock,
  Shield,
  Sparkles,
  ShieldCheck,
  Server,
  Fingerprint,
  type LucideIcon,
} from 'lucide-react'

interface LoginProps {
  onLogin: (user: User) => void
}

const featureHighlights: Array<{
  icon: LucideIcon
  title: string
  description: string
}> = [
  {
    icon: ShieldCheck,
    title: 'Zero-trust by design',
    description: 'Secrets are encrypted locally with AES-256 before leaving your browser.',
  },
  {
    icon: Server,
    title: 'Auditable storage',
    description: 'Tamper-evident audit logs track every read, write, and deletion event.',
  },
  {
    icon: Fingerprint,
    title: 'Adaptive MFA ready',
    description: 'Plug-and-play with hardware keys, OTP, or SSO providers in minutes.',
  },
]

export default function Login({ onLogin }: LoginProps) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const { toast } = useToast()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      const response = await api.login(username, password)
      api.setTokens(response.access_token, response.refresh_token)
      // Helpful console for session debugging
      console.info('[Auth] Login session info', response.session || '(no session)')
      onLogin(response.user)
      toast({
        title: 'Success',
        description: 'Logged in successfully',
      })
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: error instanceof Error ? error.message : 'Login failed',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-aurora text-white">
      <div className="absolute inset-0 bg-slate-950/75" />
      <div className="absolute inset-0 bg-soft-grid opacity-20" />
      <div className="pointer-events-none absolute -top-40 -left-32 h-80 w-80 rounded-full bg-primary/30 blur-3xl animate-slow-float" />
      <div className="pointer-events-none absolute -bottom-56 -right-40 h-[420px] w-[420px] rounded-full bg-indigo-500/25 blur-3xl animate-slower-float" />

      <div className="relative z-10 mx-auto flex min-h-screen w-full items-center justify-center px-6 py-16">
        <div className="grid w-full max-w-6xl items-center gap-12 lg:grid-cols-[1.15fr_0.85fr]">
          <div className="hidden max-w-xl flex-col gap-10 lg:flex">
            <span className="badge-pill border-white/30 bg-white/10 text-white/70">
              <Sparkles className="h-4 w-4" />
              <span>Secure-ity Platform</span>
            </span>
            <div className="space-y-4">
              <h1 className="text-4xl font-bold leading-tight sm:text-5xl">
                Sign in to your secure control center
              </h1>
              <p className="text-lg text-white/70">
                Manage secrets, enforce policies, and ship compliant releases faster.
                Your configurations stay encrypted from browser to database.
              </p>
            </div>
            <div className="grid gap-6 sm:grid-cols-2">
              {featureHighlights.map((feature) => {
                const Icon = feature.icon
                return (
                  <div
                    key={feature.title}
                    className="rounded-2xl border border-white/10 bg-white/5 p-5 backdrop-blur-xl transition-transform duration-300 hover:-translate-y-1"
                  >
                    <Icon className="mb-3 h-6 w-6 text-white/80" />
                    <h3 className="text-base font-semibold text-white">{feature.title}</h3>
                    <p className="mt-2 text-sm text-white/70">{feature.description}</p>
                  </div>
                )
              })}
            </div>
          </div>

          <Card className="glass-surface relative w-full max-w-md rounded-3xl border-white/30 text-slate-900 shadow-[0_38px_120px_-60px_rgba(76,29,149,0.85)]">
            <CardHeader className="space-y-4 text-center">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/15">
                <Shield className="h-7 w-7 text-primary" />
              </div>
              <div className="space-y-2">
                <CardTitle className="text-3xl font-bold text-slate-900">
                  Welcome back
                </CardTitle>
                <CardDescription className="text-base text-slate-600">
                  Authenticate to unlock your encrypted configuration vault
                </CardDescription>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              <form onSubmit={handleSubmit} className="space-y-5">
                <div className="space-y-2 text-left">
                  <Label htmlFor="username">Username</Label>
                  <Input
                    id="username"
                    type="text"
                    placeholder="Enter your username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    required
                    disabled={loading}
                  />
                </div>
                <div className="space-y-2 text-left">
                  <Label htmlFor="password">Password</Label>
                  <Input
                    id="password"
                    type="password"
                    placeholder="Enter your password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    disabled={loading}
                  />
                </div>
                <Button type="submit" className="w-full" disabled={loading}>
                  {loading ? (
                    'Logging in...'
                  ) : (
                    <>
                      <Lock className="mr-2 h-4 w-4" />
                      Login
                    </>
                  )}
                </Button>
              </form>
              <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-5 py-4 text-sm text-slate-600">
                <p className="font-medium">New to Secure-ity?</p>
                <p className="mt-1">
                  Request access or create an account to start managing encrypted configs.
                </p>
              </div>
              <div className="text-center text-sm text-slate-600">
                Don't have an account yet?{' '}
                <Link to="/register" className="font-semibold text-primary hover:underline">
                  Register
                </Link>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

