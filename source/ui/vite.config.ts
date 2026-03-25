// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import react from '@vitejs/plugin-react'
import { resolve } from 'node:path'
import { defineConfig, UserConfig } from 'vite'
import { CoverageV8Options, UserConfig as VitestUserConfig } from 'vitest/node'

const coverageConfig: { provider: 'v8' } & CoverageV8Options = {
  provider: 'v8',
  enabled: true,
  reportsDirectory: resolve(__dirname, './coverage'),
  reporter: ['text', 'lcov'],
  exclude: [
    './src/index.tsx',
    './src/setupTests.ts',
    './build/**',
    './index.html',
    './vite.config.ts',
  ],
}

// https://vitejs.dev/config/
const config: VitestUserConfig & UserConfig = {
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/setupTests.ts'],
    include: ['./src/__test__/**/*.test.ts?(x)'],
    coverage: coverageConfig,
    css: false,
  },
  plugins: [react()],
  build: {
    outDir: resolve(__dirname, './build'),
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          cloudscape: ['@cloudscape-design/components', '@cloudscape-design/global-styles'],
          amplify: ['aws-amplify'],
        },
      },
    },
  },
  server: {
    port: 3000,
    open: true,
  },
  define: {
    global: 'globalThis',
  },
}

export default defineConfig(config)
