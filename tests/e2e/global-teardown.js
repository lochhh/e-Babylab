import { execSync } from 'child_process'
import { fileURLToPath } from 'url'
import { dirname, resolve } from 'path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT = resolve(__dirname, '../..')

export default async function globalTeardown() {
  execSync(
    'docker compose -f docker-compose.dev.yml exec -T web uv run python manage.py delete_e2e_fixtures',
    { stdio: 'inherit', cwd: ROOT },
  )
}
