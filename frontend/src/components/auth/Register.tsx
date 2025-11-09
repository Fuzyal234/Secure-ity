import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api, User } from '@/lib/api'
import { useToast } from '@/components/ui/use-toast'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  UserPlus,
  Shield,
  Sparkles,
  ShieldCheck,
  KeyRound,
  ClipboardCheck,
  type LucideIcon,
} from 'lucide-react'

interface RegisterProps {
  onLogin: (user: User) => void
}

const onboardingHighlights: Array<{
  icon: LucideIcon
  title: string
  description: string
}> = [
  {
    icon: ShieldCheck,
    title: 'IR-ready controls',
    description: 'Meet STIG & SOC2 requirements out of the box with enforced security baselines.',
  },
  {
    icon: KeyRound,
    title: 'Secrets lifecycle',
    description: 'Rotate, revoke, and version sensitive configs from a centralized vault.',
  },
  {
    icon: ClipboardCheck,
    title: 'Policy automation',
    description: 'Gate deployments with RBAC approvals and automated compliance workflows.',
  },
]

export default function Register({ onLogin }: RegisterProps) {
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const { toast } = useToast()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      await api.register(username, email, password)
      toast({
        title: 'Success',
        description: 'Registration successful! Please login.',
      })
      // Auto-login after registration
      const loginResponse = await api.login(username, password)
      api.setTokens(loginResponse.access_token, loginResponse.refresh_token)
      onLogin(loginResponse.user)
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: error instanceof Error ? error.message : 'Registration failed',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-aurora text-white">
      <div className="absolute inset-0 bg-slate-950/75" />
      <div className="absolute inset-0 bg-soft-grid opacity-20" />
      <div className="pointer-events-none absolute -top-48 right-[-120px] h-[420px] w-[420px] rounded-full bg-primary/25 blur-3xl animate-slow-float" />
      <div className="pointer-events-none absolute -bottom-64 left-[-160px] h-[460px] w-[460px] rounded-full bg-indigo-500/25 blur-3xl animate-slower-float" />

      <div className="relative z-10 mx-auto flex min-h-screen w-full items-center justify-center px-6 py-16">
        <div className="grid w-full max-w-6xl items-center gap-12 lg:grid-cols-[1.15fr_0.85fr]">
          <div className="hidden max-w-xl flex-col gap-10 lg:flex">
            <span className="badge-pill border-white/30 bg-white/10 text-white/70">
              <Sparkles className="h-4 w-4" />
              <span>Secure-ity Platform</span>
            </span>
            <div className="space-y-4">
              <h1 className="text-4xl font-bold leading-tight sm:text-5xl">
                Create your security seat in minutes
              </h1>
              <p className="text-lg text-white/70">
                Streamline onboarding with automated key management and guardrails that scale
                from proof-of-concept to enterprise rollouts.
              </p>
            </div>
            <div className="grid gap-6 sm:grid-cols-2">
              {onboardingHighlights.map((item) => {
                const Icon = item.icon
                return (
                  <div
                    key={item.title}
                    className="rounded-2xl border border-white/10 bg-white/5 p-5 backdrop-blur-xl transition-transform duration-300 hover:-translate-y-1"
                  >
                    <Icon className="mb-3 h-6 w-6 text-white/80" />
                    <h3 className="text-base font-semibold text-white">{item.title}</h3>
                    <p className="mt-2 text-sm text-white/70">{item.description}</p>
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
                  Create your account
                </CardTitle>
                <CardDescription className="text-base text-slate-600">
                  Provision a seat and start orchestrating secure configuration workflows
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
                    placeholder="Choose a username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    required
                    disabled={loading}
                  />
                </div>
                <div className="space-y-2 text-left">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="you@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    disabled={loading}
                  />
                </div>
                <div className="space-y-2 text-left">
                  <Label htmlFor="password">Password</Label>
                  <Input
                    id="password"
                    type="password"
                    placeholder="Min 12 chars, uppercase, lowercase, number, special"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    disabled={loading}
                  />
                  <p className="text-xs text-slate-500">
                    Password must be at least 12 characters long and include mixed character types.
                  </p>
                </div>
                <Button type="submit" className="w-full" disabled={loading}>
                  {loading ? (
                    'Creating account...'
                  ) : (
                    <>
                      <UserPlus className="mr-2 h-4 w-4" />
                      Register
                    </>
                  )}
                </Button>
              </form>
              <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-5 py-4 text-sm text-slate-600">
                <p className="font-medium">Enterprise rollout?</p>
                <p className="mt-1">
                  Invite teammates and enforce policy controls once you're inside the dashboard.
                </p>
              </div>
              <div className="text-center text-sm text-slate-600">
                Already have an account?{' '}
                <Link to="/login" className="font-semibold text-primary hover:underline">
                  Login
                </Link>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

