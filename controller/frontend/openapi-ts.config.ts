import { defineConfig } from '@hey-api/openapi-ts';

const apiInput = process.env.NODE_ENV === 'production'
  ? '../backend/openapi.json'
  : 'http://localhost:8000/openapi.json';


export default defineConfig({
  input: apiInput,
  output: {
    path: 'src/sdk',
    source: true,
    watch: true,
  },
  plugins: ['@hey-api/sdk'],
});
