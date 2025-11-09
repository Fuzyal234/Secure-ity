import { useState, useEffect } from 'react'
import { api, Config } from '@/lib/api'
import { useToast } from '@/components/ui/use-toast'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Plus,
  RefreshCw,
  Eye,
  Trash2,
  Lock,
  FileText,
  ShieldCheck,
  Sparkles,
  Cpu,
} from 'lucide-react'
import ConfigForm from './ConfigForm'
import ConfigView from './ConfigView'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'

export default function Dashboard() {
  const [configs, setConfigs] = useState<Config[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [selectedConfig, setSelectedConfig] = useState<Config | null>(null)
  const [deleteId, setDeleteId] = useState<number | null>(null)
  const { toast } = useToast()

  const loadConfigs = async () => {
    setLoading(true)
    try {
      const response = await api.getConfigs()
      setConfigs(response.configs)
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to load configurations',
      })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadConfigs()
  }, [])

  const handleCreateSuccess = () => {
    setShowForm(false)
    loadConfigs()
    toast({
      title: 'Success',
      description: 'Configuration created successfully',
    })
  }

  const handleDelete = async () => {
    if (!deleteId) return
    try {
      await api.deleteConfig(deleteId)
      toast({
        title: 'Success',
        description: 'Configuration deleted successfully',
      })
      loadConfigs()
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to delete configuration',
      })
    } finally {
      setDeleteId(null)
    }
  }

  const handleViewConfig = async (id: number) => {
    try {
      const config = await api.getConfig(id)
      setSelectedConfig(config)
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to load configuration',
      })
    }
  }

  if (showForm) {
    return (
      <ConfigForm
        onSuccess={handleCreateSuccess}
        onCancel={() => setShowForm(false)}
      />
    )
  }

  if (selectedConfig) {
    return (
      <ConfigView
        config={selectedConfig}
        onClose={() => setSelectedConfig(null)}
      />
    )
  }

  return (
    <div className="space-y-8">
      <section className="relative overflow-hidden rounded-3xl border border-primary/20 bg-white/85 p-8 shadow-xl backdrop-blur">
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-primary/10 via-transparent to-indigo-100/40" />
        <div className="pointer-events-none absolute -top-24 right-16 h-48 w-48 rounded-full bg-primary/15 blur-3xl" />
        <div className="relative flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-5">
            <span className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-4 py-1 text-xs font-semibold uppercase tracking-[0.35em] text-primary">
              <Sparkles className="h-4 w-4" />
              Configuration vault
            </span>
            <div className="space-y-3">
              <h2 className="text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
                Your encrypted configuration control center
              </h2>
              <p className="max-w-2xl text-base text-slate-600">
                View versioned secrets, monitor access, and collaborate with fine-grained RBAC—without exposing sensitive data.
              </p>
            </div>
            <div className="flex flex-wrap gap-3 text-sm text-slate-600">
              <span className="inline-flex items-center gap-2 rounded-full bg-white/80 px-4 py-2 shadow-sm backdrop-blur">
                <ShieldCheck className="h-4 w-4 text-primary" />
                AES-256 encryption
              </span>
              <span className="inline-flex items-center gap-2 rounded-full bg-white/80 px-4 py-2 shadow-sm backdrop-blur">
                <Cpu className="h-4 w-4 text-primary" />
                Policy-driven automation
              </span>
              <span className="inline-flex items-center gap-2 rounded-full bg-white/80 px-4 py-2 shadow-sm backdrop-blur">
                <RefreshCw className="h-4 w-4 text-primary" />
                {configs.length} config{configs.length !== 1 ? 's' : ''} in sync
              </span>
            </div>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row lg:flex-col">
            <Button size="lg" className="shadow-lg" onClick={() => setShowForm(true)}>
              <Plus className="mr-2 h-4 w-4" />
              New Configuration
            </Button>
            <Button
              size="lg"
              variant="outline"
              className="border-primary/20"
              onClick={loadConfigs}
              disabled={loading}
            >
              <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh inventory
            </Button>
          </div>
        </div>
      </section>

      <Card className="border-slate-200/60 bg-white/85 shadow-lg backdrop-blur">
        <CardHeader className="border-b border-slate-200/60 bg-white/60">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle className="text-xl text-slate-900">Encrypted inventory</CardTitle>
              <CardDescription>
                Track every configuration with audit-ready metadata and instant rollbacks.
              </CardDescription>
            </div>
            <span className="mt-2 inline-flex w-max items-center gap-2 rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-primary sm:mt-0">
              <Lock className="h-4 w-4" />
              Zero trust
            </span>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex flex-col items-center justify-center gap-3 py-16 text-slate-500">
              <RefreshCw className="h-6 w-6 animate-spin text-primary" />
              <p className="text-sm">Syncing the latest configuration inventory...</p>
            </div>
          ) : configs.length === 0 ? (
            <div className="relative overflow-hidden rounded-3xl border border-dashed border-primary/30 bg-primary/5 px-10 py-14 text-center">
              <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-primary/10 via-transparent to-transparent" />
              <div className="relative flex flex-col items-center gap-4 text-slate-600">
                <FileText className="h-12 w-12 text-primary" />
                <h3 className="text-xl font-semibold text-slate-800">
                  No configurations yet
                </h3>
                <p className="max-w-md text-sm">
                  Bootstrap your first secret bundle and we&apos;ll encrypt, version, and audit it automatically.
                </p>
                <Button onClick={() => setShowForm(true)} size="lg" className="mt-2">
                  <Plus className="mr-2 h-4 w-4" />
                  Create configuration
                </Button>
              </div>
            </div>
          ) : (
            <div className="grid gap-5">
              {configs.map((config) => (
                <div
                  key={config.id}
                  className="group relative overflow-hidden rounded-2xl border border-slate-200/70 bg-white/80 p-6 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:border-primary/40 hover:shadow-xl"
                >
                  <div className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100">
                    <div className="absolute inset-0 bg-gradient-to-r from-primary/10 via-transparent to-transparent" />
                  </div>
                  <div className="relative flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                    <div className="space-y-3">
                      <div className="flex items-center gap-3">
                        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary/10">
                          <Lock className="h-5 w-5 text-primary" />
                        </div>
                        <div>
                          <h3 className="text-lg font-semibold text-slate-900">
                            {config.name}
                          </h3>
                          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                            <span className="rounded-full bg-primary/10 px-2.5 py-1 font-medium text-primary">
                              v{config.version}
                            </span>
                            <span>Created {new Date(config.created_at).toLocaleDateString()}</span>
                            <span>•</span>
                            <span>By {config.created_by}</span>
                          </div>
                        </div>
                      </div>
                      {config.description && (
                        <p className="max-w-2xl text-sm text-slate-600">
                          {config.description}
                        </p>
                      )}
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="border-primary/30"
                        onClick={() => handleViewConfig(config.id)}
                      >
                        <Eye className="mr-2 h-4 w-4" />
                        View
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => setDeleteId(config.id)}
                      >
                        <Trash2 className="mr-2 h-4 w-4" />
                        Delete
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <AlertDialog open={deleteId !== null} onOpenChange={(open) => !open && setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Configuration</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this configuration? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete}>Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

