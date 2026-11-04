import listHiragana from './hiragana.js';
import listKanji from './kanji.js';
import toeic from './toeic.js';
import toeicv1 from './toeicv1.js';
import toeicv2 from './toeicv2.js';
import toeicv3 from './toeicv3.js';
import toeicv4 from './toeicv4.js';
import toeicIIG from './toeicIIG.js';
import { generateExampleSentences } from './gemini-sentence-service.js';

const vocabularyByPage = {
    'hiragana.html': listHiragana,
    'kanji.html': listKanji,
    'toeic.html': toeic,
    'toeicv1.html': toeicv1,
    'toeicv2.html': toeicv2,
    'toeicv3.html': toeicv3,
    'toeicv4.html': toeicv4,
    'toeicIIG.html': toeicIIG
};

const pageName = location.pathname.split('/').pop();
const vocabularyList = vocabularyByPage[pageName] || [];
const sourceLanguage = ['hiragana.html', 'kanji.html'].includes(pageName) ? 'tiếng Nhật' : 'tiếng Anh';
const sentenceLanguageCode = sourceLanguage === 'tiếng Nhật' ? 'ja' : 'en';
const flashContainer = document.getElementById('flashcards-container');
const sentenceCache = new Map();

let previousCard = null;
let renderedList = [];
let activeTerm = '';
let activeItem = null;
let activeRequest = null;
let sentenceModal = null;
let modalCloseRequested = false;

const searchContainer = document.createElement('div');
searchContainer.className = 'search-container';
searchContainer.innerHTML = '<input type="text" id="search-input" placeholder="Tìm kiếm từ vựng..." aria-label="Tìm kiếm từ vựng" />';
flashContainer.parentNode.insertBefore(searchContainer, flashContainer);

function createSentenceModal() {
    const element = document.createElement('div');
    element.className = 'modal fade';
    element.id = 'sentence-examples-modal';
    element.tabIndex = -1;
    element.dataset.bsBackdrop = 'static';
    element.setAttribute('aria-labelledby', 'sentence-examples-title');
    element.setAttribute('aria-hidden', 'true');
    element.innerHTML = `
        <div class="modal-dialog modal-dialog-centered modal-dialog-scrollable">
            <div class="modal-content sentence-modal-content">
                <div class="modal-header">
                    <div class="sentence-modal-heading">
                        <span class="sentence-modal-eyebrow">Example sentences</span>
                        <h2 class="modal-title fs-5" id="sentence-examples-title"></h2>
                    </div>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Đóng"></button>
                </div>
                <div class="modal-body" id="sentence-examples-body" aria-live="polite" aria-atomic="true"></div>
            </div>
        </div>`;
    document.body.appendChild(element);
    element.querySelector('.btn-close').addEventListener('click', () => {
        modalCloseRequested = true;
    });
    element.addEventListener('hide.bs.modal', (event) => {
        if (!modalCloseRequested) event.preventDefault();
    });
    element.addEventListener('hidden.bs.modal', () => {
        modalCloseRequested = false;
        activeRequest?.abort();
        activeRequest = null;
    });
    return element;
}

const modalElement = createSentenceModal();
const modalTitle = modalElement.querySelector('#sentence-examples-title');
const modalBody = modalElement.querySelector('#sentence-examples-body');

function renderCards(list) {
    renderedList = list;
    previousCard = null;
    const fragment = document.createDocumentFragment();

    list.forEach((item, index) => {
        const card = document.createElement('div');
        card.className = 'col-md-3 flashcard';
        const front = document.createElement('div');
        front.className = 'front';
        front.textContent = item.tv;
        const back = document.createElement('div');
        back.className = 'back';
        back.textContent = item.mean;
        const trigger = document.createElement('button');
        trigger.type = 'button';
        trigger.className = 'btn sentence-trigger';
        trigger.dataset.cardIndex = index;
        trigger.setAttribute('aria-label', `Xem 10 câu ví dụ cho ${item.tv}`);
        trigger.title = 'Câu ví dụ';
        trigger.innerHTML = `
            <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <path d="M7.5 18.5 3 21v-5.2A8 8 0 0 1 2 12c0-4.4 4.25-8 9.5-8S21 7.6 21 12s-4.25 8-9.5 8c-1.42 0-2.77-.26-4-.73Z" />
                <path d="M7 10.5h9M7 14h6" />
            </svg>`;
        card.append(front, back, trigger);
        fragment.appendChild(card);
    });

    flashContainer.replaceChildren(fragment);
}

function renderLoading() {
    modalBody.innerHTML = `
        <div class="sentence-modal-state">
            <div class="spinner-border text-danger" role="status"><span class="visually-hidden">Đang tải</span></div>
            <p>Đang tạo 10 câu ví dụ...</p>
        </div>`;
}

function renderError(message) {
    modalBody.innerHTML = `
        <div class="sentence-modal-state sentence-modal-error" role="alert">
            <p></p>
            <button type="button" class="btn sentence-retry">Thử lại</button>
        </div>`;
    modalBody.querySelector('p').textContent = message;
}

function renderEmpty(message) {
    modalBody.innerHTML = '<div class="sentence-modal-state sentence-modal-empty"><p></p></div>';
    modalBody.querySelector('p').textContent = message;
}

function renderSentences(sentences) {
    const list = document.createElement('ul');
    list.className = 'sentence-examples-list';

    sentences.forEach(({ word, sentence, translation }) => {
        const item = document.createElement('li');
        item.className = 'sentence-example-item';
        const sentenceText = document.createElement('p');
        sentenceText.className = 'sentence-example-english';
        sentenceText.lang = sentenceLanguageCode;
        sentenceText.textContent = sentence;
        const meta = document.createElement('div');
        meta.className = 'sentence-example-meta';
        const badge = document.createElement('span');
        badge.className = 'sentence-word-badge';
        badge.textContent = word;
        const translationText = document.createElement('p');
        translationText.className = 'sentence-example-translation';
        translationText.lang = 'vi';
        translationText.textContent = translation;
        meta.append(badge, translationText);
        item.append(sentenceText, meta);
        list.appendChild(item);
    });

    modalBody.replaceChildren(list);
}

async function loadSentences(item, forceReload = false) {
    const term = item.tv;
    activeRequest?.abort();
    activeTerm = term;
    activeItem = item;

    if (!forceReload && sentenceCache.has(term)) {
        activeRequest = null;
        renderSentences(sentenceCache.get(term));
        return;
    }

    const controller = new AbortController();
    activeRequest = controller;
    renderLoading();
    try {
        const sentences = await generateExampleSentences(term, item.mean, sourceLanguage, controller.signal);
        if (activeRequest !== controller || activeTerm !== term) return;
        sentenceCache.set(term, sentences);
        renderSentences(sentences);
    } catch (error) {
        if (error.name !== 'AbortError' && activeRequest === controller && activeTerm === term) {
            if (error.code === 'EMPTY_RESULT') renderEmpty(error.message);
            else renderError(error.message || 'Không thể tạo câu ví dụ.');
        }
    } finally {
        if (activeRequest === controller) activeRequest = null;
    }
}

flashContainer.addEventListener('click', (event) => {
    const trigger = event.target.closest('.sentence-trigger');
    if (trigger) {
        event.stopPropagation();
        const item = renderedList[Number(trigger.dataset.cardIndex)];
        if (!item) return;
        modalTitle.textContent = `Câu ví dụ cho “${item.tv}”`;
        sentenceModal ||= new bootstrap.Modal(modalElement, { backdrop: 'static' });
        sentenceModal.show();
        loadSentences(item);
        return;
    }

    const card = event.target.closest('.flashcard');
    if (!card) return;
    flipCard(card, previousCard);
    previousCard = card;
});

modalBody.addEventListener('click', (event) => {
    if (event.target.closest('.sentence-retry') && activeItem) loadSentences(activeItem, true);
});

function shuffled(items) {
    const copy = [...items];
    for (let index = copy.length - 1; index > 0; index -= 1) {
        const randomIndex = Math.floor(Math.random() * (index + 1));
        [copy[index], copy[randomIndex]] = [copy[randomIndex], copy[index]];
    }
    return copy;
}

renderCards(shuffled(vocabularyList));

document.getElementById('search-input').addEventListener('input', (event) => {
    const searchTerm = event.target.value.toLowerCase().trim();
    renderCards(searchTerm
        ? vocabularyList.filter((item) => item.tv.toLowerCase().includes(searchTerm))
        : shuffled(vocabularyList));
});
