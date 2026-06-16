module.exports = {
  apps: [
    {
      name: 'alwrity-frontend',
      cwd: '/mnt/blockstorage/workspace/ALwrity/frontend/build',
      script: '/usr/bin/python3',
      args: '-m http.server 3001 --bind 127.0.0.1',
      interpreter: 'none',
      autorestart: true,
      max_restarts: 20,
      restart_delay: 3000,
      out_file: '/mnt/blockstorage/workspace/ALwrity/logs/frontend.out.log',
      error_file: '/mnt/blockstorage/workspace/ALwrity/logs/frontend.err.log',
      merge_logs: true,
      env: {
        NODE_ENV: 'production'
      }
    },
    {
      name: 'alwrity-backend',
      cwd: '/mnt/blockstorage/workspace/ALwrity/backend',
      script: '/mnt/blockstorage/workspace/ALwrity/backend/.venv/bin/python',
      args: '-m uvicorn app:app --host 127.0.0.1 --port 8000',
      interpreter: 'none',
      autorestart: true,
      max_restarts: 20,
      restart_delay: 5000,
      out_file: '/mnt/blockstorage/workspace/ALwrity/logs/backend.out.log',
      error_file: '/mnt/blockstorage/workspace/ALwrity/logs/backend.err.log',
      merge_logs: true,
      env: {
        PORT: '8000',
        HOST: '127.0.0.1',
        ALWRITY_ENABLED_FEATURES: 'podcast',
        STRIPE_PLAN_PRICE_MAPPING_TEST: '{"basic":{"monthly":"price_test_basic_monthly"},"pro":{"monthly":"price_test_pro_monthly"}}'
      }
    }
  ]
};
