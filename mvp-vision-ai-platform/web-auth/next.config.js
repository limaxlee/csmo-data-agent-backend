/** @type {import('next').NextConfig} */

function normalizeBasePath(value) {
  const raw = (value || '').trim()
  if (!raw || raw === '/') return ''
  return `/${raw.replace(/^\/+|\/+$/g, '')}`
}

// 배포 시 NEXT_PUBLIC_BASE_PATH="/" 로 설정
// basePath 는 "/" 일 때 비워둠 (root 에서 서빙)
const basePath = normalizeBasePath(process.env.NEXT_PUBLIC_BASE_PATH || '/')

const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  ...(basePath ? { basePath } : {}),
  env: {
    NEXT_PUBLIC_BASE_PATH: basePath,
  },
}

module.exports = nextConfig

