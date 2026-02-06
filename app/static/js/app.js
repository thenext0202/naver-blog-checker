document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('searchForm');
    const submitBtn = document.getElementById('submitBtn');
    const btnText = document.getElementById('btnText');
    const loadingIcon = document.getElementById('loadingIcon');
    const resultArea = document.getElementById('resultArea');
    const exposureSummary = document.getElementById('exposureSummary');
    const resultsList = document.getElementById('resultsList');
    const totalCount = document.getElementById('totalCount');
    const errorArea = document.getElementById('errorArea');
    const errorMessage = document.getElementById('errorMessage');

    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        const keyword = document.getElementById('keyword').value.trim();
        const blogUrl = document.getElementById('blogUrl').value.trim();

        if (!keyword || !blogUrl) {
            showError('키워드와 글 URL을 모두 입력해주세요.');
            return;
        }

        // UI 상태 변경
        setLoading(true);
        hideError();
        hideResults();

        try {
            const response = await fetch('/api/check-exposure', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    keyword: keyword,
                    blog_url: blogUrl
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || '요청 처리 중 오류가 발생했습니다.');
            }

            if (!data.success) {
                showError(data.message || '검색 중 오류가 발생했습니다.');
                return;
            }

            displayResults(data);

        } catch (error) {
            showError(error.message || '서버와 통신 중 오류가 발생했습니다.');
        } finally {
            setLoading(false);
        }
    });

    function setLoading(isLoading) {
        submitBtn.disabled = isLoading;
        if (isLoading) {
            btnText.textContent = '검색 중...';
            loadingIcon.classList.remove('hidden');
            submitBtn.classList.add('opacity-75', 'cursor-not-allowed');
        } else {
            btnText.textContent = '노출 체크하기';
            loadingIcon.classList.add('hidden');
            submitBtn.classList.remove('opacity-75', 'cursor-not-allowed');
        }
    }

    function showError(message) {
        errorMessage.textContent = message;
        errorArea.classList.remove('hidden');
    }

    function hideError() {
        errorArea.classList.add('hidden');
    }

    function hideResults() {
        resultArea.classList.add('hidden');
    }

    function displayResults(data) {
        // 노출 요약 표시
        if (data.is_exposed) {
            exposureSummary.innerHTML = `
                <div class="text-center">
                    <div class="inline-flex items-center justify-center w-16 h-16 bg-green-100 rounded-full mb-4">
                        <svg class="w-8 h-8 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                        </svg>
                    </div>
                    <h2 class="text-2xl font-bold text-green-600 mb-2">노출됨!</h2>
                    <p class="text-gray-600 mb-4">'<span class="font-semibold">${escapeHtml(data.keyword)}</span>' 검색 시</p>
                    <div class="inline-block bg-green-50 rounded-lg px-6 py-3">
                        <span class="text-4xl font-bold text-green-600">${data.exposed_rank}</span>
                        <span class="text-gray-600">위</span>
                    </div>
                    ${data.exposed_result ? `
                        <div class="mt-4 p-4 bg-gray-50 rounded-lg text-left">
                            <p class="font-semibold text-gray-800 mb-1">${escapeHtml(data.exposed_result.title)}</p>
                            <p class="text-sm text-gray-500">${escapeHtml(data.exposed_result.blog_name)} · ${escapeHtml(data.exposed_result.date)}</p>
                            <a href="${escapeHtml(data.exposed_result.url)}" target="_blank" class="text-sm text-green-600 hover:underline break-all">${escapeHtml(data.exposed_result.url)}</a>
                        </div>
                    ` : ''}
                </div>
            `;
        } else {
            exposureSummary.innerHTML = `
                <div class="text-center">
                    <div class="inline-flex items-center justify-center w-16 h-16 bg-red-100 rounded-full mb-4">
                        <svg class="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                    </div>
                    <h2 class="text-2xl font-bold text-red-600 mb-2">노출되지 않음</h2>
                    <p class="text-gray-600">'<span class="font-semibold">${escapeHtml(data.keyword)}</span>' 검색 결과</p>
                    <p class="text-gray-500 text-sm mt-2">상위 ${data.total_results}개 결과에 해당 글이 노출되지 않습니다.</p>
                </div>
            `;
        }

        // 검색 결과 목록 표시
        totalCount.textContent = `(총 ${data.total_results}개)`;

        if (data.results && data.results.length > 0) {
            resultsList.innerHTML = data.results.map((result, index) => `
                <div class="p-4 border rounded-lg ${data.is_exposed && result.rank === data.exposed_rank ? 'border-green-500 bg-green-50' : 'border-gray-200 hover:border-gray-300'} transition">
                    <div class="flex items-start gap-3">
                        <div class="flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-full ${data.is_exposed && result.rank === data.exposed_rank ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-600'} font-semibold text-sm">
                            ${result.rank}
                        </div>
                        <div class="flex-1 min-w-0">
                            <a href="${escapeHtml(result.url)}" target="_blank" class="font-semibold text-gray-800 hover:text-green-600 line-clamp-1">
                                ${escapeHtml(result.title)}
                            </a>
                            <p class="text-sm text-gray-600 mt-1 line-clamp-2">${escapeHtml(result.description)}</p>
                            <div class="flex items-center gap-2 mt-2 text-xs text-gray-500">
                                <span>${escapeHtml(result.blog_name)}</span>
                                ${result.date ? `<span>·</span><span>${escapeHtml(result.date)}</span>` : ''}
                            </div>
                        </div>
                    </div>
                </div>
            `).join('');
        } else {
            resultsList.innerHTML = '<p class="text-center text-gray-500">검색 결과가 없습니다.</p>';
        }

        resultArea.classList.remove('hidden');
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
});
