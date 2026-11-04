import { SENTENCE_API_URL } from './api-config.js';

export async function generateExampleSentences(term, definition, sourceLanguage, signal) {
    const response = await fetch(SENTENCE_API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal,
        body: JSON.stringify({ term, definition, sourceLanguage })
    });

    const payload = await response.json().catch(() => null);
    if (!response.ok) {
        const error = new Error(payload?.error || `Sentence API gặp lỗi (${response.status}).`);
        error.code = payload?.code;
        throw error;
    }

    if (!Array.isArray(payload?.sentences) || payload.sentences.length !== 10) {
        throw new Error('Sentence API không trả về đúng 10 câu.');
    }

    return payload.sentences;
}
