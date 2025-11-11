import { Config } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ArrowLeft, Lock, Calendar, User, Tag, ShieldCheck, Sparkles } from 'lucide-react'

interface ConfigViewProps {
  config: Config
  onClose: () => void
}

export default function ConfigView({ config, onClose }: ConfigViewProps) {
  const hasDecrypted = config.data !== undefined && config.data !== null
  const hasEncrypted =
    !!config.encrypted_data &&
    !!config.iv &&
    !!config.encryption_algorithm &&
    !!config.key_version

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <Button
        variant="ghost"
        onClick={onClose}
        className="w-fit rounded-full border border-primary/20 bg-primary/5 px-4"
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to configurations
      </Button>

      <div className="grid gap-8 lg:grid-cols-[2fr_1fr]">
        <Card className="border-primary/20 bg-white/85 shadow-lg backdrop-blur">
          <CardHeader className="space-y-4 border-b border-slate-200/60 bg-white/60">
            <div className="inline-flex w-fit items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.3em] text-primary">
              <Lock className="h-4 w-4" />
              {hasDecrypted ? 'Decrypted view' : hasEncrypted ? 'Encrypted view' : 'No payload'}
            </div>
            <div className="space-y-2">
              <CardTitle className="flex flex-wrap items-center gap-3 text-2xl text-slate-900">
                {config.name}
              </CardTitle>
              {config.description && (
                <CardDescription className="text-base text-slate-600">
                  {config.description}
                </CardDescription>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-6 pt-6">
            <div className="flex flex-wrap gap-3 text-xs text-slate-600">
              <span className="inline-flex items-center gap-2 rounded-full bg-primary/10 px-3 py-1 font-semibold text-primary">
                <Tag className="h-4 w-4" />
                Version {config.version}
              </span>
              <span className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1">
                <Calendar className="h-4 w-4" />
                Created {new Date(config.created_at).toLocaleDateString()}
              </span>
              <span className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1">
                <Calendar className="h-4 w-4" />
                Updated {new Date(config.updated_at).toLocaleDateString()}
              </span>
              <span className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1">
                <User className="h-4 w-4" />
                {config.created_by}
              </span>
            </div>

            {hasDecrypted && (
              <div className="space-y-3">
                <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-800">
                  <Lock className="h-4 w-4 text-primary" />
                  Decrypted configuration payload
                </h3>
                <div className="overflow-hidden rounded-3xl border border-slate-900/10 bg-slate-950 text-slate-50 shadow-inner">
                  <div className="flex items-center justify-between border-b border-white/10 px-5 py-3 text-xs uppercase tracking-[0.3em] text-white/60">
                    <span>AES-256 GCM</span>
                    <span>Decrypted on demand</span>
                  </div>
                  <pre className="max-h-96 overflow-auto bg-transparent px-6 py-5 text-sm text-emerald-100/95">
                    {JSON.stringify(config.data, null, 2)}
                  </pre>
                </div>
                <p className="text-xs text-slate-500">
                  Rendered only for this session. We never persist decrypted payloads—refreshing the view will request a new decryption event.
                </p>
              </div>
            )}

            {!hasDecrypted && hasEncrypted && (
              <div className="space-y-3">
                <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-800">
                  <Lock className="h-4 w-4 text-primary" />
                  Encrypted configuration payload
                </h3>
                <div className="overflow-hidden rounded-3xl border border-slate-900/10 bg-slate-950 text-slate-50 shadow-inner">
                  <div className="flex items-center justify-between border-b border-white/10 px-5 py-3 text-xs uppercase tracking-[0.3em] text-white/60">
                    <span>{(config.encryption_algorithm || 'AES-256-GCM').toUpperCase()}</span>
                    <span>Encrypted at rest</span>
                  </div>
                  <pre className="max-h-96 overflow-auto bg-transparent px-6 py-5 text-sm text-emerald-100/95">
{JSON.stringify({
  ciphertext: config.encrypted_data,
  iv: config.iv,
  algorithm: config.encryption_algorithm,
  key_version: config.key_version,
  data_hash: config.data_hash,
}, null, 2)}
                  </pre>
                </div>
                <p className="text-xs text-slate-500">
                  As an administrator, you can view ciphertext and metadata for auditing. Plaintext is not shown unless you are the creator of this configuration.
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card className="border-primary/20 bg-white/85 shadow-lg backdrop-blur">
            <CardHeader className="space-y-3">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-5 w-5 text-primary" />
                <CardTitle className="text-lg text-slate-900">Metadata</CardTitle>
              </div>
              <CardDescription className="text-sm text-slate-600">
                Quick facts to support incident response, audits, and rollbacks.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-1">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Version</p>
                <p className="text-sm font-semibold text-slate-900">v{config.version}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Created</p>
                <p className="text-sm font-semibold text-slate-900">
                  {new Date(config.created_at).toLocaleString()}
                </p>
              </div>
              <div className="space-y-1">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Updated</p>
                <p className="text-sm font-semibold text-slate-900">
                  {new Date(config.updated_at).toLocaleString()}
                </p>
              </div>
              <div className="space-y-1">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Created by</p>
                <p className="text-sm font-semibold text-slate-900">{config.created_by}</p>
              </div>
            </CardContent>
          </Card>

          <Card className="relative overflow-hidden border border-dashed border-primary/30 bg-primary/5 shadow-none">
            <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-primary/10 via-transparent to-transparent" />
            <CardContent className="relative space-y-3 p-6">
              <div className="flex items-center gap-3">
                <Sparkles className="h-5 w-5 text-primary" />
                <h3 className="text-sm font-semibold text-slate-900">Security tip</h3>
              </div>
              <p className="text-sm text-slate-600">
                Rotate sensitive values by creating a new configuration version. Secure-ity automatically tracks diffs and stores the previous copy for instant rollback.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

