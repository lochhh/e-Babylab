import { execSync } from 'child_process'
import { fileURLToPath } from 'url'
import { dirname, resolve } from 'path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT = resolve(__dirname, '../..')

export default async function globalSetup() {
  execSync(
    'docker compose -f docker-compose.dev.yml exec -T web uv run python manage.py create_e2e_fixtures',
    { stdio: 'inherit', cwd: ROOT },
  )
}
