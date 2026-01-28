# NOW-029: Crear Profile.tsx

## Metadata
- **Prioridad**: P1
- **Fase**: 3 - Dashboard
- **Dependencias**: NOW-008, NOW-009
- **Archivos a crear**: `dashboard/src/pages/Profile.tsx`
- **Tiempo estimado**: 3-4 horas

## Descripción
Crear la página de perfil del worker con Bayesian score, historial de tareas, earnings y configuración.

## Contexto Técnico
- **Framework**: React + TailwindCSS
- **State**: TanStack Query (React Query)
- **Data**: Supabase RPC functions

## Wireframe

```
┌─────────────────────────────────────────────────────────────┐
│  ← Back                                    [Settings] [⚙️]  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│    ┌──────────┐                                             │
│    │  Avatar  │    John Doe                                 │
│    │   (JD)   │    0x1234...5678                           │
│    └──────────┘    Member since Jan 2026                   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│    │   72.5      │  │   $125.50   │  │    15       │       │
│    │ Reputation  │  │  Earnings   │  │   Tasks     │       │
│    └─────────────┘  └─────────────┘  └─────────────┘       │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  Seals & Badges                                             │
│  ┌────────┐ ┌────────┐ ┌────────┐                          │
│  │ ⭐ TOP │ │ 🎯 REL │ │ ⚡ FAST│                          │
│  │ WORKER │ │ IABLE  │ │ PAYER  │                          │
│  └────────┘ └────────┘ └────────┘                          │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  Recent Activity                                    See all │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ✅ Photo verification - $5.00       2 hours ago    │   │
│  │ ✅ Store check - $3.50              Yesterday      │   │
│  │ ⏳ Delivery pickup - $8.00          In progress    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  Earnings                                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Available: $45.50    [Withdraw]                    │   │
│  │  Pending:   $8.00                                   │   │
│  │  Total:     $125.50                                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Código de Referencia

```tsx
// dashboard/src/pages/Profile.tsx
import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/lib/supabase';
import { useAuth } from '@/hooks/useAuth';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { formatCurrency, formatAddress, formatRelativeTime } from '@/lib/utils';

export default function Profile() {
  const { user, executorId } = useAuth();

  // Fetch profile data
  const { data: profile, isLoading: profileLoading } = useQuery({
    queryKey: ['profile', executorId],
    queryFn: async () => {
      const { data } = await supabase
        .from('executors')
        .select('*')
        .eq('id', executorId)
        .single();
      return data;
    },
    enabled: !!executorId
  });

  // Fetch stats
  const { data: stats } = useQuery({
    queryKey: ['profile-stats', executorId],
    queryFn: async () => {
      // Get Bayesian score
      const { data: score } = await supabase
        .rpc('calculate_bayesian_score', { p_executor_id: executorId });

      // Get earnings
      const { data: earnings } = await supabase
        .from('payments')
        .select('amount_usdc, status')
        .eq('executor_id', executorId);

      const completed = earnings?.filter(e => e.status === 'completed') || [];
      const pending = earnings?.filter(e => e.status === 'pending') || [];

      // Get task count
      const { count: taskCount } = await supabase
        .from('submissions')
        .select('*', { count: 'exact', head: true })
        .eq('executor_id', executorId)
        .eq('status', 'approved');

      return {
        reputation: score || 50,
        totalEarnings: completed.reduce((sum, e) => sum + parseFloat(e.amount_usdc), 0),
        pendingEarnings: pending.reduce((sum, e) => sum + parseFloat(e.amount_usdc), 0),
        tasksCompleted: taskCount || 0
      };
    },
    enabled: !!executorId
  });

  // Fetch recent activity
  const { data: recentActivity } = useQuery({
    queryKey: ['profile-activity', executorId],
    queryFn: async () => {
      const { data } = await supabase
        .from('submissions')
        .select(`
          id,
          status,
          created_at,
          tasks (
            title,
            bounty_usdc
          )
        `)
        .eq('executor_id', executorId)
        .order('created_at', { ascending: false })
        .limit(5);
      return data;
    },
    enabled: !!executorId
  });

  // Fetch seals
  const { data: seals } = useQuery({
    queryKey: ['profile-seals', executorId],
    queryFn: async () => {
      const { data } = await supabase
        .from('worker_seals')
        .select('*')
        .eq('executor_id', executorId);
      return data || [];
    },
    enabled: !!executorId
  });

  if (profileLoading) {
    return <ProfileSkeleton />;
  }

  return (
    <div className="container max-w-2xl mx-auto py-8 px-4">
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <div className="w-20 h-20 rounded-full bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center text-white text-2xl font-bold">
          {profile?.email?.[0]?.toUpperCase() || 'W'}
        </div>
        <div>
          <h1 className="text-2xl font-bold">{profile?.name || 'Worker'}</h1>
          <p className="text-gray-500 font-mono text-sm">
            {formatAddress(profile?.wallet_address)}
          </p>
          <p className="text-gray-400 text-sm">
            Member since {new Date(profile?.created_at).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}
          </p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <StatCard
          label="Reputation"
          value={stats?.reputation?.toFixed(1) || '50.0'}
          color={getReputationColor(stats?.reputation)}
        />
        <StatCard
          label="Earnings"
          value={formatCurrency(stats?.totalEarnings || 0)}
        />
        <StatCard
          label="Tasks"
          value={stats?.tasksCompleted?.toString() || '0'}
        />
      </div>

      {/* Seals */}
      {seals && seals.length > 0 && (
        <section className="mb-8">
          <h2 className="text-lg font-semibold mb-3">Seals & Badges</h2>
          <div className="flex flex-wrap gap-2">
            {seals.map(seal => (
              <Badge key={seal.id} variant="outline" className="px-3 py-1">
                {getSealEmoji(seal.seal_type)} {seal.seal_name}
              </Badge>
            ))}
          </div>
        </section>
      )}

      {/* Recent Activity */}
      <section className="mb-8">
        <div className="flex justify-between items-center mb-3">
          <h2 className="text-lg font-semibold">Recent Activity</h2>
          <Button variant="link" size="sm">See all</Button>
        </div>
        <div className="space-y-2">
          {recentActivity?.map(activity => (
            <ActivityItem key={activity.id} activity={activity} />
          )) || <p className="text-gray-500">No recent activity</p>}
        </div>
      </section>

      {/* Earnings */}
      <section className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4">
        <h2 className="text-lg font-semibold mb-3">Earnings</h2>
        <div className="space-y-2">
          <div className="flex justify-between">
            <span>Available</span>
            <span className="font-semibold text-green-600">
              {formatCurrency((stats?.totalEarnings || 0) - (stats?.pendingEarnings || 0))}
            </span>
          </div>
          <div className="flex justify-between">
            <span>Pending</span>
            <span className="text-gray-500">{formatCurrency(stats?.pendingEarnings || 0)}</span>
          </div>
          <hr className="my-2" />
          <div className="flex justify-between">
            <span>Total Earned</span>
            <span className="font-bold">{formatCurrency(stats?.totalEarnings || 0)}</span>
          </div>
        </div>
        <Button className="w-full mt-4" disabled={(stats?.totalEarnings || 0) < 5}>
          Withdraw
        </Button>
        {(stats?.totalEarnings || 0) < 5 && (
          <p className="text-xs text-gray-500 text-center mt-2">
            Minimum withdrawal: $5.00
          </p>
        )}
      </section>
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-4 text-center shadow-sm">
      <div className={`text-2xl font-bold ${color || ''}`}>{value}</div>
      <div className="text-sm text-gray-500">{label}</div>
    </div>
  );
}

function ActivityItem({ activity }: { activity: any }) {
  const statusIcon = {
    approved: '✅',
    pending_review: '⏳',
    rejected: '❌'
  }[activity.status] || '•';

  return (
    <div className="flex items-center justify-between py-2 px-3 bg-white dark:bg-gray-800 rounded">
      <div className="flex items-center gap-2">
        <span>{statusIcon}</span>
        <span>{activity.tasks?.title}</span>
      </div>
      <div className="text-right">
        <div className="font-semibold">{formatCurrency(activity.tasks?.bounty_usdc)}</div>
        <div className="text-xs text-gray-500">{formatRelativeTime(activity.created_at)}</div>
      </div>
    </div>
  );
}

function getReputationColor(score?: number): string {
  if (!score) return '';
  if (score >= 80) return 'text-green-600';
  if (score >= 60) return 'text-yellow-600';
  return 'text-red-600';
}

function getSealEmoji(type: string): string {
  const emojis: Record<string, string> = {
    TOP_WORKER: '⭐',
    RELIABLE: '🎯',
    FAST_PAYER: '⚡',
    VERIFIED: '✓',
    SKILLFUL: '🏆'
  };
  return emojis[type] || '•';
}

function ProfileSkeleton() {
  return (
    <div className="container max-w-2xl mx-auto py-8 px-4">
      <div className="flex items-center gap-4 mb-8">
        <Skeleton className="w-20 h-20 rounded-full" />
        <div>
          <Skeleton className="h-8 w-32 mb-2" />
          <Skeleton className="h-4 w-48" />
        </div>
      </div>
      <div className="grid grid-cols-3 gap-4 mb-8">
        <Skeleton className="h-24 rounded-lg" />
        <Skeleton className="h-24 rounded-lg" />
        <Skeleton className="h-24 rounded-lg" />
      </div>
    </div>
  );
}
```

## Criterios de Éxito
- [ ] Página renderiza sin errores
- [ ] Profile data carga correctamente
- [ ] Stats (reputation, earnings, tasks) calculados
- [ ] Recent activity muestra últimas 5 submissions
- [ ] Seals se muestran si existen
- [ ] Withdraw button funcional
- [ ] Loading states con skeletons
- [ ] Responsive design

## Test Cases
```typescript
// Test 1: Profile loads
render(<Profile />);
await waitFor(() => {
  expect(screen.getByText('Reputation')).toBeInTheDocument();
});

// Test 2: Stats display correctly
expect(screen.getByText('$125.50')).toBeInTheDocument();

// Test 3: Withdraw disabled when < $5
const withdrawBtn = screen.getByRole('button', { name: /withdraw/i });
expect(withdrawBtn).toBeDisabled();
```
