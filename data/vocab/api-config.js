const VERCEL_PROJECT_ORIGIN = 'https://app-nihongo.vercel.app';

export const SENTENCE_API_URL = location.hostname.endsWith('.vercel.app')
    ? '/api/generate-sentences'
    : `${VERCEL_PROJECT_ORIGIN}/api/generate-sentences`;
