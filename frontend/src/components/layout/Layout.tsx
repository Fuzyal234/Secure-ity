import { ReactNode } from 'react'
import { User, api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Shield, LogOut, User as UserIcon } from 'lucide-react'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'

interface LayoutProps {
  children: ReactNode
  user: User
  onLogout: () => void
}

export default function Layout({ children, user, onLogout }: LayoutProps) {
  return (
    <div className="relative min-h-screen overflow-hidden bg-gradient-to-br from-[#f6f3ff] via-white to-[#e8f3ff]">
      <div className="pointer-events-none absolute -top-40 -right-52 h-96 w-96 rounded-full bg-primary/20 blur-3xl" />
      <div className="pointer-events-none absolute bottom-[-160px] left-[-120px] h-[420px] w-[420px] rounded-full bg-sky-300/25 blur-3xl" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(99,102,241,0.12)_0,_transparent_55%),radial-gradient(circle_at_bottom,_rgba(14,165,233,0.12)_0,_transparent_45%)]" />

      <header className="relative z-20 border-b border-white/60 bg-white/80 backdrop-blur-xl">
        <div className="container mx-auto flex items-center justify-between px-4 py-4">
          <div className="flex items-center space-x-3">
            <div className="rounded-xl bg-primary/10 p-2">
              <Shield className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-foreground">Secure-ity</h1>
              <p className="text-xs tracking-wide text-muted-foreground">
                Secure configuration management platform
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 rounded-full border border-slate-200 bg-white/70 px-3 py-1.5 text-sm shadow-sm backdrop-blur">
              <UserIcon className="h-4 w-4 text-muted-foreground" />
              <span className="font-medium text-foreground">{user.username}</span>
              <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-semibold uppercase tracking-wide text-primary">
                {user.role}
              </span>
            </div>
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="outline" size="sm" className="border-primary/20">
                  <LogOut className="mr-2 h-4 w-4" />
                  Logout
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Ready to sign out?</AlertDialogTitle>
                  <AlertDialogDescription>
                    We will close your session and revoke refresh tokens across devices.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Stay signed in</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={() => {
                      api.logoutApi().then(() => onLogout())
                    }}
                  >
                    Logout
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        </div>
      </header>

      <main className="relative z-10 container mx-auto px-4 py-10">
        {children}
      </main>
    </div>
  )
}

