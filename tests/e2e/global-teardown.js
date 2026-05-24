import { execSync } from 'child_process'
import { fileURLToPath } from 'url'
import { dirname, resolve } from 'path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT = resolve(__dirname, '../..')

// IDs match MODES in create_e2e_fixtures.py
const SUBJECT_IDS = [
  'b0e2e000-0000-0000-0000-000000000001',
  'b0e2e000-0000-0000-0000-000000000002',
  'b0e2e000-0000-0000-0000-000000000003',
  'b0e2e000-0000-0000-0000-000000000004',
  'b0e2e000-0000-0000-0000-000000000005',
]
const EXP_IDS = [
  'a0e2e000-0000-0000-0000-000000000001',
  'a0e2e000-0000-0000-0000-000000000002',
  'a0e2e000-0000-0000-0000-000000000003',
  'a0e2e000-0000-0000-0000-000000000004',
  'a0e2e000-0000-0000-0000-000000000005',
]

export default async function globalTeardown() {
  const subjectList = SUBJECT_IDS.map(id => `'${id}'`).join(', ')
  const expList = EXP_IDS.map(id => `'${id}'`).join(', ')
  execSync(
    `docker compose -f docker-compose.dev.yml exec -T web uv run python manage.py shell -c "
from experiments.models import SubjectData, Experiment, TrialResult
TrialResult.objects.filter(subject_id__in=[${subjectList}]).delete()
SubjectData.objects.filter(id__in=[${subjectList}]).delete()
Experiment.objects.filter(id__in=[${expList}]).delete()
print('e2e fixtures cleaned up')
"`,
    { stdio: 'inherit', cwd: ROOT },
  )
}
