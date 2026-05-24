import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const nm = path.join(__dirname, 'node_modules')

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',

  webpack: (config) => {
    config.resolve.alias = {
      ...config.resolve.alias,
      'victory-vendor/d3-shape': path.join(nm, 'victory-vendor/lib/d3-shape.js'),
      'victory-vendor/d3-scale': path.join(nm, 'victory-vendor/lib/d3-scale.js'),
    }

    return config
  },
}

export default nextConfig