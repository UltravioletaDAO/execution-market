# NOW-010: Configurar Supabase Storage bucket 'evidence'

## Metadata
- **Prioridad**: P0
- **Fase**: 0 - Infrastructure
- **Dependencias**: NOW-008
- **Archivos a crear**: `supabase/migrations/006_storage_policies.sql`
- **Tiempo estimado**: 30 min

## Descripción
Crear y configurar el bucket de Storage para almacenar evidence de tareas completadas.

## Contexto Técnico
- **Bucket name**: `evidence`
- **Público**: No (requiere auth)
- **Max file size**: 50MB
- **Tipos permitidos**: JPEG, PNG, MP4, PDF
- **Estructura**: `evidence/{task_id}/{submission_id}/{filename}`

## Configuración via Dashboard

1. Ir a **Storage** en Supabase Dashboard
2. Click **New Bucket**
3. Configurar:
   - Name: `evidence`
   - Public: OFF
   - File size limit: 52428800 (50MB)
   - Allowed MIME types: `image/jpeg,image/png,video/mp4,application/pdf`

## Código de Referencia

### 006_storage_policies.sql
```sql
-- Create the bucket (if not using dashboard)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'evidence',
  'evidence',
  false,
  52428800, -- 50MB
  ARRAY['image/jpeg', 'image/png', 'video/mp4', 'application/pdf']
)
ON CONFLICT (id) DO UPDATE
SET
  file_size_limit = EXCLUDED.file_size_limit,
  allowed_mime_types = EXCLUDED.allowed_mime_types;

-- ===========================================
-- Storage Policies
-- ===========================================

-- Policy: Authenticated users can upload evidence
CREATE POLICY "Users can upload evidence"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
  bucket_id = 'evidence'
  AND (storage.foldername(name))[1] IS NOT NULL -- task_id folder required
);

-- Policy: Users can view their own submissions' evidence
CREATE POLICY "Users can view evidence for their submissions"
ON storage.objects FOR SELECT
TO authenticated
USING (
  bucket_id = 'evidence'
  AND EXISTS (
    SELECT 1 FROM submissions s
    JOIN executors e ON s.executor_id = e.id
    WHERE (storage.foldername(name))[2] = s.id::text
      AND e.id = auth.uid()
  )
);

-- Policy: Agents can view evidence for their tasks
CREATE POLICY "Agents can view evidence for their tasks"
ON storage.objects FOR SELECT
TO authenticated
USING (
  bucket_id = 'evidence'
  AND EXISTS (
    SELECT 1 FROM tasks t
    WHERE (storage.foldername(name))[1] = t.id::text
      AND t.agent_id = auth.jwt() ->> 'sub'
  )
);

-- Policy: Service role can do anything (for backend)
CREATE POLICY "Service role has full access"
ON storage.objects
TO service_role
USING (bucket_id = 'evidence')
WITH CHECK (bucket_id = 'evidence');
```

## Estructura de Archivos

```
evidence/
├── {task_id}/
│   ├── {submission_id}/
│   │   ├── photo_1.jpg
│   │   ├── photo_2.jpg
│   │   └── receipt.pdf
│   └── {another_submission_id}/
│       └── video.mp4
└── {another_task_id}/
    └── ...
```

## Criterios de Éxito
- [ ] Bucket 'evidence' creado
- [ ] File size limit = 50MB
- [ ] MIME types restringidos
- [ ] Policy de upload funciona
- [ ] Policy de read funciona
- [ ] No acceso público sin auth

## Comandos de Verificación

```typescript
// Test upload
const file = new File(['test'], 'test.jpg', { type: 'image/jpeg' });
const { data, error } = await supabase.storage
  .from('evidence')
  .upload(`${taskId}/${submissionId}/test.jpg`, file);

// Test download
const { data: url } = await supabase.storage
  .from('evidence')
  .createSignedUrl(`${taskId}/${submissionId}/test.jpg`, 3600);

// List files
const { data: files } = await supabase.storage
  .from('evidence')
  .list(`${taskId}/${submissionId}`);
```

## Upload Flow desde Dashboard

```typescript
// dashboard/src/lib/storage.ts
export async function uploadEvidence(
  taskId: string,
  submissionId: string,
  file: File
): Promise<string> {
  const timestamp = Date.now();
  const extension = file.name.split('.').pop();
  const path = `${taskId}/${submissionId}/${timestamp}.${extension}`;

  const { data, error } = await supabase.storage
    .from('evidence')
    .upload(path, file, {
      cacheControl: '3600',
      upsert: false
    });

  if (error) throw error;

  // Get signed URL for verification
  const { data: urlData } = await supabase.storage
    .from('evidence')
    .createSignedUrl(path, 86400); // 24 hours

  return urlData.signedUrl;
}
```

## Cleanup Job (opcional)
```sql
-- Delete evidence older than 90 days for completed tasks
CREATE OR REPLACE FUNCTION cleanup_old_evidence()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  -- Mark for deletion (actual deletion via scheduled job)
  UPDATE storage.objects
  SET metadata = jsonb_set(
    COALESCE(metadata, '{}'::jsonb),
    '{marked_for_deletion}',
    'true'
  )
  WHERE bucket_id = 'evidence'
    AND created_at < NOW() - INTERVAL '90 days';
END;
$$;
```
